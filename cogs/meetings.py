# Cog Réunions (cogs/meetings.py)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from datetime import datetime
import logging
import json
from config import ADMIN_ROLES
from database import Database
from .admin import is_admin

logger = logging.getLogger(__name__)


# cog de gestion des réunions
class MeetingsCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.active_meetings = {}

    # Création d'une réunion
    @app_commands.command(name="meeting_create", description="Créer une réunion")
    @app_commands.describe(
        titre="Titre de la réunion",
        date="Date de la réunion (JJ/MM/AAAA)",
        heure="Heure de la réunion (HH:MM)",
        roles='Rôles ciblés ("ALL", "DEV", "IA", "INFRA" ou combinaison "DEV,IA")',
        description="Description de la réunion (optionnel)",
    )
    @is_admin()
    async def create_meeting(
        self,
        interaction: discord.Interaction,
        titre: str,
        date: str,
        heure: str,
        roles: Optional[str] = "ALL",
        description: Optional[str] = None,
    ):
        await interaction.response.defer()

        # Parser la date et heure
        try:
            datetime_str = f"{date} {heure}"
            meeting_date = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
        except ValueError:
            await interaction.followup.send(
                "❌ Format invalide!\nDate: JJ/MM/AAAA\nHeure: HH:MM"
            )
            return

        # Vérifier que la date est dans le futur
        if meeting_date <= datetime.now():
            await interaction.followup.send("❌ La réunion doit être dans le futur!")
            return

        # Parser les rôles ciblés
        if roles.upper() == "ALL":
            target_roles = ["ALL"]
        else:
            target_roles = [r.strip().upper() for r in roles.split(",")]
            valid_roles = ["DEV", "IA", "INFRA"]
            for role in target_roles:
                if role not in valid_roles:
                    await interaction.followup.send(
                        f"❌ Rôle invalide: {role}\nRôles valides: {', '.join(valid_roles)}"
                    )
                    return

        # Récupérer l'organisateur
        organizer = self.db.get_member(str(interaction.user.id))
        if not organizer:
            await interaction.followup.send(
                "❌ Vous devez être enregistré comme membre pour créer une réunion"
            )
            return

        # Créer la réunion
        meeting = self.db.create_meeting(
            title=titre,
            date=meeting_date,
            description=description,
            created_by=str(interaction.user.id),
            organizer_id=organizer.id,
            target_roles=target_roles,
        )

        # Créer l'embed de confirmation
        embed = discord.Embed(
            title="✅ Réunion créée",
            color=discord.Color.green(),
            timestamp=meeting_date,
        )
        embed.add_field(name="📝 Titre", value=titre, inline=False)
        embed.add_field(name="📅 Date", value=date, inline=True)
        embed.add_field(name="⏰ Heure", value=heure, inline=True)
        embed.add_field(
            name="👥 Pôles concernés",
            value="Tous" if "ALL" in target_roles else ", ".join(target_roles),
            inline=True,
        )
        if description:
            embed.add_field(name="📋 Description", value=description, inline=False)
        embed.set_footer(text=f"Organisée par {interaction.user.display_name}")

        # Mentionner les rôles concernés
        mentions = []
        if "ALL" in target_roles:
            mentions.append("@everyone")
        else:
            for role_name in target_roles:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    mentions.append(role.mention)

        await interaction.followup.send(
            content=" ".join(mentions) if mentions else None, embed=embed
        )

    # Lancer l'appel pour une réunion par nom
    @app_commands.command(
        name="appel", description="Faire l'appel pour une réunion (nom partiel)"
    )
    @app_commands.describe(reunion="Nom ou partie du nom de la réunion")
    @is_admin()
    async def start_attendance(self, interaction: discord.Interaction, reunion: str):
        await interaction.response.defer()

        # Rechercher la réunion par nom
        meetings = self.db.get_meeting_by_name(reunion)

        if not meetings:
            await interaction.followup.send(
                f"❌ Aucune réunion trouvée avec le nom '{reunion}'"
            )
            return

        if len(meetings) > 1:
            # Plusieurs réunions trouvées, demander de préciser
            embed = discord.Embed(
                title="⚠️ Plusieurs réunions trouvées",
                description="Veuillez préciser en utilisant l'ID:",
                color=discord.Color.orange(),
            )
            for meeting in meetings[:5]:  # Limiter à 5
                embed.add_field(
                    name=f"#{meeting.id} - {meeting.title}",
                    value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}\n"
                    f"Organisateur: <@{meeting.created_by}>",
                    inline=False,
                )
            embed.set_footer(text="Utilisez: /appel_id [id]")
            await interaction.followup.send(embed=embed)
            return

        meeting = meetings[0]

        # Empêcher de relancer l'appel si déjà validé
        if meeting.attendance_validated:
            await interaction.followup.send(
                "❌ L'appel pour cette réunion a déjà été validé et ne peut pas être relancé"
            )
            return

        # Créer la vue Admin pour gérer l'appel
        await self._create_attendance_view(interaction, meeting)

    # Lancer l'appel pour une réunion par ID
    @app_commands.command(
        name="appel_id", description="Faire l'appel par ID de réunion"
    )
    @app_commands.describe(meeting_id="ID de la réunion")
    @is_admin()
    async def start_attendance_by_id(
        self, interaction: discord.Interaction, meeting_id: int
    ):
        await interaction.response.defer()

        meeting = self.db.get_meeting(meeting_id)
        if not meeting:
            await interaction.followup.send("❌ Réunion introuvable")
            return

        if meeting.attendance_validated:
            await interaction.followup.send(
                "❌ L'appel pour cette réunion a déjà été validé"
            )
            return

        # Créer la vue Admin pour gérer l'appel
        await self._create_attendance_view(interaction, meeting)

    async def _create_attendance_view(self, interaction, meeting):
        """Méthode helper pour créer et afficher la vue d'appel admin"""
        target_roles = meeting.get_target_roles()
        roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

        # Récupérer les membres attendus
        expected_members = self.db.get_members_by_roles(target_roles)

        # Créer l'embed principal
        embed = discord.Embed(
            title=f"📢 Appel Administratif - {meeting.title}",
            description=f"**Réunion ID:** {meeting.id}\n"
            f"**Pôles concernés:** {roles_text}\n"
            f"**Membres attendus:** {len(expected_members)}\n\n"
            "Utilisez l'interface ci-dessous pour gérer l'appel.",
            color=discord.Color.blue(),
            timestamp=meeting.date,
        )

        embed.add_field(
            name="📅 Date de la réunion",
            value=meeting.date.strftime("%d/%m/%Y à %H:%M"),
            inline=False,
        )

        # Créer la vue Admin
        admin_view = AdminAttendanceView(
            meeting.id, self.db, str(interaction.user.id), expected_members
        )

        # Envoyer le message avec la vue
        message = await interaction.followup.send(embed=embed, view=admin_view)
        self.active_meetings[meeting.id] = message

    # Statistiques d'une réunion par ID
    @app_commands.command(
        name="meeting_stats_id",
        description="Voir les statistiques d'une réunion passée",
    )
    @app_commands.describe(meeting_id="ID de la réunion à consulter")
    async def meeting_stats_id(self, interaction: discord.Interaction, meeting_id: int):
        await interaction.response.defer()

        stats = self.db.get_meeting_stats(meeting_id)
        if not stats:
            await interaction.followup.send("❌ Réunion introuvable", ephemeral=True)
            return

        meeting_data = stats["meeting_data"]
        embed = discord.Embed(
            title=f"📊 Statistiques - {meeting_data['title']}",
            description=f"Date: {meeting_data['date'].strftime('%d/%m/%Y %H:%M')}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name="✅ Présents", value=stats["present"], inline=True)
        embed.add_field(name="❌ Absents", value=stats["absent"], inline=True)
        embed.add_field(name="🏥 Excusés", value=stats["excused"], inline=True)
        embed.add_field(name="🎯 Attendus", value=stats["expected"], inline=True)
        embed.add_field(
            name="📈 Taux de participation", value=f"{stats['rate']:.1f}%", inline=True
        )

        await interaction.followup.send(embed=embed)

    # Statistiques d'une réunion par nom
    @app_commands.command(
        name="meeting_stats",
        description="Voir les statistiques d'une réunion (nom partiel)",
    )
    @app_commands.describe(reunion="Nom ou partie du nom de la réunion")
    async def meeting_stats(self, interaction: discord.Interaction, reunion: str):
        await interaction.response.defer()

        meetings = self.db.get_meeting_by_name(reunion)
        if not meetings:
            await interaction.followup.send(
                f"❌ Aucune réunion trouvée avec le nom '{reunion}'", ephemeral=True
            )
            return

        if len(meetings) > 1:
            embed = discord.Embed(
                title="⚠️ Plusieurs réunions trouvées",
                description="Veuillez préciser en utilisant l'ID:",
                color=discord.Color.orange(),
            )
            for meeting in meetings[:5]:
                embed.add_field(
                    name=f"#{meeting.id} - {meeting.title}",
                    value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}\n"
                    f"Organisateur: <@{meeting.created_by}>",
                    inline=False,
                )
            embed.set_footer(text="Utilisez: /meeting_stats_id [id]")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        meeting = meetings[0]
        stats = self.db.get_meeting_stats(meeting.id)
        if not stats:
            await interaction.followup.send("❌ Réunion introuvable", ephemeral=True)
            return

        meeting_data = stats["meeting_data"]
        embed = discord.Embed(
            title=f"📊 Statistiques - {meeting_data['title']}",
            description=f"Date: {meeting_data['date'].strftime('%d/%m/%Y %H:%M')}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name="✅ Présents", value=stats["present"], inline=True)
        embed.add_field(name="❌ Absents", value=stats["absent"], inline=True)
        embed.add_field(name="🏥 Excusés", value=stats["excused"], inline=True)
        embed.add_field(name="🎯 Attendus", value=stats["expected"], inline=True)
        embed.add_field(
            name="📈 Taux de participation", value=f"{stats['rate']:.1f}%", inline=True
        )

        await interaction.followup.send(embed=embed)

    # Modifier la présence par ID de réunion
    @app_commands.command(
        name="modifier_presence_id",
        description="Modifier la présence d'un membre (par ID réunion)",
    )
    @app_commands.describe(
        meeting_id="ID de la réunion",
        membre="Membre Discord",
        statut="present/absent/excused",
    )
    @is_admin()
    async def modify_attendance_by_id(
        self,
        interaction: discord.Interaction,
        meeting_id: int,
        membre: discord.Member,
        statut: str,
    ):
        await interaction.response.defer(ephemeral=True)

        meeting = self.db.get_meeting(meeting_id)
        if not meeting:
            await interaction.followup.send("❌ Réunion introuvable", ephemeral=True)
            return

        if not meeting.attendance_validated:
            await interaction.followup.send(
                "❌ L'appel n'a pas encore été validé pour cette réunion",
                ephemeral=True,
            )
            return

        member = self.db.get_member(str(membre.id))
        if not member:
            await interaction.followup.send("❌ Membre non enregistré", ephemeral=True)
            return

        valid_statuses = ["present", "absent", "excused"]
        if statut not in valid_statuses:
            await interaction.followup.send(
                f"❌ Statut invalide. Utilisez: {', '.join(valid_statuses)}",
                ephemeral=True,
            )
            return

        self.db.record_attendance(
            meeting.id, member.id, statut, modified_by=str(interaction.user.id)
        )

        await interaction.followup.send(
            f"✅ Présence modifiée: {membre.mention} → {statut}", ephemeral=True
        )

    # Modifier la présence par nom de réunion
    @app_commands.command(
        name="modifier_presence", description="Modifier la présence d'un membre"
    )
    @app_commands.describe(
        reunion="Nom ou partie du nom de la réunion",
        membre="Membre Discord",
        statut="present/absent/excused",
    )
    @is_admin()
    async def modify_attendance(
        self,
        interaction: discord.Interaction,
        reunion: str,
        membre: discord.Member,
        statut: str,
    ):
        await interaction.response.defer(ephemeral=True)

        # Rechercher la réunion
        meetings = self.db.get_meeting_by_name(reunion)

        if not meetings:
            await interaction.followup.send(
                f"❌ Aucune réunion trouvée", ephemeral=True
            )
            return

        if len(meetings) > 1:
            embed = discord.Embed(
                title="⚠️ Plusieurs réunions trouvées",
                description="Précisez en utilisant l'ID: /modifier_presence_id [id]",
                color=discord.Color.orange(),
            )
            for meeting in meetings[:10]:
                embed.add_field(
                    name=f"#{meeting.id} - {meeting.title}",
                    value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}",
                    inline=False,
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        meeting = meetings[0]

        if not meeting.attendance_validated:
            await interaction.followup.send(
                "❌ L'appel n'a pas encore été validé pour cette réunion",
                ephemeral=True,
            )
            return

        member = self.db.get_member(str(membre.id))
        if not member:
            await interaction.followup.send("❌ Membre non enregistré", ephemeral=True)
            return

        valid_statuses = ["present", "absent", "excused"]
        if statut not in valid_statuses:
            await interaction.followup.send(
                f"❌ Statut invalide. Utilisez: {', '.join(valid_statuses)}",
                ephemeral=True,
            )
            return

        self.db.record_attendance(
            meeting.id, member.id, statut, modified_by=str(interaction.user.id)
        )

        await interaction.followup.send(
            f"✅ Présence modifiée: {membre.mention} → {statut}", ephemeral=True
        )

    # Afficher les prochaines réunions
    @app_commands.command(
        name="meetings", description="Afficher les prochaines réunions"
    )
    @app_commands.describe(pole="Filtrer par pôle (DEV, IA, INFRA) - optionnel")
    async def list_meetings(
        self, interaction: discord.Interaction, pole: Optional[str] = None
    ):
        await interaction.response.defer()

        meetings = self.db.get_upcoming_meetings(
            limit=10, role=pole.upper() if pole else None
        )

        if not meetings:
            msg = "Aucune réunion prévue"
            if pole:
                msg += f" pour le pôle {pole.upper()}"
            await interaction.followup.send(msg)
            return

        # Créer l'embed
        title = "📅 Prochaines réunions"
        if pole:
            title += f" - Pôle {pole.upper()}"

        embed = discord.Embed(
            title=title, color=discord.Color.blue(), timestamp=discord.utils.utcnow()
        )

        for meeting in meetings:
            target_roles = meeting.get_target_roles()
            roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

            field_value = f"📅 {meeting.date.strftime('%d/%m/%Y à %H:%M')}\n"
            field_value += f"👥 Pôles: {roles_text}\n"
            if meeting.description:
                field_value += f"📝 {meeting.description[:100]}..."

            embed.add_field(name=f"{meeting.title}", value=field_value, inline=False)

        await interaction.followup.send(embed=embed)


# Vue Admin améliorée pour gérer l'appel complet
class AdminAttendanceView(discord.ui.View):
    """Vue pour les admins permettant de faire l'appel complet avec gestion
    individuelle de chaque membre et validation finale."""

    def __init__(self, meeting_id, db, initiator_id, expected_members):
        super().__init__(timeout=1800)  # 30 minutes
        self.meeting_id = meeting_id
        self.db = db
        self.initiator_id = initiator_id
        self.members = expected_members
        self.page = 0
        self.members_per_page = 5
        self.attendance_status = {}  # {member_id: status}
        self.validated = False

        # Initialiser avec les statuts existants en base de données
        self._load_existing_attendance()

    def _load_existing_attendance(self):
        """Charger les présences déjà enregistrées"""
        attendances = self.db.get_meeting_attendance(self.meeting_id)
        for att, member in attendances:
            self.attendance_status[member.id] = att.status

    def get_current_page_members(self):
        """Récupérer les membres de la page actuelle"""
        start = self.page * self.members_per_page
        end = start + self.members_per_page
        return self.members[start:end]

    def get_total_pages(self):
        """Calculer le nombre total de pages"""
        return (len(self.members) - 1) // self.members_per_page + 1

    @discord.ui.select(
        placeholder="Sélectionner un membre...", min_values=1, max_values=1, row=0
    )
    async def member_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        """Sélecteur de membre pour la page actuelle"""
        # Le select sera mis à jour dynamiquement
        pass

    @discord.ui.button(label="✅ Présent", style=discord.ButtonStyle.success, row=1)
    async def mark_present(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._mark_status(interaction, "present")

    @discord.ui.button(label="❌ Absent", style=discord.ButtonStyle.danger, row=1)
    async def mark_absent(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._mark_status(interaction, "absent")

    @discord.ui.button(label="🏥 Excusé", style=discord.ButtonStyle.secondary, row=1)
    async def mark_excused(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._mark_status(interaction, "excused")

    async def _mark_status(self, interaction: discord.Interaction, status: str):
        """Marquer le statut du membre sélectionné"""
        if not hasattr(self, "selected_member_id") or not self.selected_member_id:
            await interaction.response.send_message(
                "⚠️ Veuillez d'abord sélectionner un membre dans la liste",
                ephemeral=True,
            )
            return

        # Enregistrer le statut
        self.attendance_status[self.selected_member_id] = status

        # Persister en base de données
        self.db.record_attendance(
            self.meeting_id,
            self.selected_member_id,
            status,
            modified_by=str(interaction.user.id),
        )

        # Trouver le membre pour afficher son nom
        member_name = "Membre"
        for m in self.members:
            if m.id == self.selected_member_id:
                member_name = m.full_name or m.username
                break

        await interaction.response.send_message(
            f"✅ {member_name} marqué comme {status}", ephemeral=True
        )

        # Rafraîchir l'affichage
        await self.update_display(interaction)

    @discord.ui.button(
        label="◀ Page précédente", style=discord.ButtonStyle.primary, row=2
    )
    async def prev_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page > 0:
            self.page -= 1
            await self.update_display(interaction)
        else:
            await interaction.response.send_message(
                "Vous êtes déjà à la première page", ephemeral=True
            )

    @discord.ui.button(
        label="Page suivante ▶", style=discord.ButtonStyle.primary, row=2
    )
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page < self.get_total_pages() - 1:
            self.page += 1
            await self.update_display(interaction)
        else:
            await interaction.response.send_message(
                "Vous êtes déjà à la dernière page", ephemeral=True
            )

    @discord.ui.button(
        label="🔄 Rafraîchir", style=discord.ButtonStyle.secondary, row=3
    )
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.update_display(interaction)

    @discord.ui.button(
        label="📋 Valider l'appel", style=discord.ButtonStyle.danger, row=3
    )
    async def validate_attendance(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Valider définitivement l'appel"""
        if self.validated:
            await interaction.response.send_message(
                "✅ L'appel a déjà été validé", ephemeral=True
            )
            return

        # Vérifier que l'utilisateur est autorisé
        if str(interaction.user.id) != self.initiator_id:
            member = self.db.get_member(str(interaction.user.id))
            is_admin = any(role.name in ADMIN_ROLES for role in interaction.user.roles)
            if not is_admin:
                await interaction.response.send_message(
                    "❌ Seul un administrateur peut valider l'appel", ephemeral=True
                )
                return

        # Marquer les membres non marqués comme absents
        for member in self.members:
            if member.id not in self.attendance_status:
                self.attendance_status[member.id] = "absent"
                self.db.record_attendance(
                    self.meeting_id,
                    member.id,
                    "absent",
                    modified_by=str(interaction.user.id),
                )

        # Valider l'appel en base de données
        self.db.validate_attendance(self.meeting_id, str(interaction.user.id))
        self.validated = True

        # Désactiver tous les boutons
        for item in self.children:
            item.disabled = True

        # Créer le rapport final
        present = sum(1 for s in self.attendance_status.values() if s == "present")
        absent = sum(1 for s in self.attendance_status.values() if s == "absent")
        excused = sum(1 for s in self.attendance_status.values() if s == "excused")
        total = len(self.members)
        rate = (present / total * 100) if total > 0 else 0

        embed = discord.Embed(
            title="✅ Appel validé",
            description=f"L'appel a été validé avec succès",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="✅ Présents", value=f"{present}/{total}", inline=True)
        embed.add_field(name="❌ Absents", value=f"{absent}/{total}", inline=True)
        embed.add_field(name="🏥 Excusés", value=f"{excused}/{total}", inline=True)
        embed.add_field(name="📈 Taux", value=f"{rate:.1f}%", inline=True)
        embed.set_footer(text=f"Validé par {interaction.user.display_name}")

        await interaction.response.edit_message(embed=embed, view=self)

    async def update_display(self, interaction: discord.Interaction):
        """Mettre à jour l'affichage avec la page actuelle"""
        if self.validated:
            return

        meeting = self.db.get_meeting(self.meeting_id)
        target_roles = meeting.get_target_roles()
        roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

        # Calculer les statistiques actuelles
        present = sum(1 for s in self.attendance_status.values() if s == "present")
        absent = sum(1 for s in self.attendance_status.values() if s == "absent")
        excused = sum(1 for s in self.attendance_status.values() if s == "excused")
        marked = present + absent + excused
        total = len(self.members)

        # Créer l'embed
        embed = discord.Embed(
            title=f"📢 Appel - {meeting.title}",
            description=f"**Page {self.page + 1}/{self.get_total_pages()}**\n"
            f"**Pôles:** {roles_text}\n"
            f"**Progression:** {marked}/{total} membres traités",
            color=discord.Color.blue(),
        )

        # Statistiques actuelles
        embed.add_field(
            name="📊 Statut actuel",
            value=f"✅ Présents: {present}\n❌ Absents: {absent}\n🏥 Excusés: {excused}",
            inline=True,
        )

        # Liste des membres de la page actuelle
        page_members = self.get_current_page_members()
        members_list = []

        # Mettre à jour le select avec les membres de la page
        select_options = []

        for i, member in enumerate(page_members, 1):
            status = self.attendance_status.get(member.id, "Non marqué")
            status_icon = {
                "present": "✅",
                "absent": "❌",
                "excused": "🏥",
                "Non marqué": "⏳",
            }.get(status, "⏳")

            member_display = f"{i}. {status_icon} {member.full_name or member.username} ({member.role})"
            members_list.append(member_display)

            # Ajouter l'option au select
            select_option = discord.SelectOption(
                label=f"{member.full_name or member.username}",
                value=str(member.id),
                description=f"{member.role} - {status}",
                emoji=status_icon,
            )
            select_options.append(select_option)

        embed.add_field(
            name="👥 Membres de cette page",
            value="\n".join(members_list) if members_list else "Aucun membre",
            inline=False,
        )

        # Mettre à jour le select
        if select_options:
            # Trouver et mettre à jour le select existant
            for item in self.children:
                if isinstance(item, discord.ui.Select):
                    item.options = select_options

                    # Définir le callback pour gérer la sélection
                    async def select_callback(select_interaction: discord.Interaction):
                        self.selected_member_id = int(item.values[0])
                        # Trouver le nom du membre sélectionné
                        selected_name = "Membre"
                        for m in self.members:
                            if m.id == self.selected_member_id:
                                selected_name = m.full_name or m.username
                                break
                        await select_interaction.response.send_message(
                            f"✅ {selected_name} sélectionné. Choisissez maintenant son statut.",
                            ephemeral=True,
                        )

                    item.callback = select_callback
                    break
            else:
                # Si pas de select trouvé, en créer un
                select = discord.ui.Select(
                    placeholder="Sélectionner un membre...",
                    min_values=1,
                    max_values=1,
                    options=select_options,
                    row=0,
                )

                async def select_callback(select_interaction: discord.Interaction):
                    self.selected_member_id = int(select.values[0])
                    selected_name = "Membre"
                    for m in self.members:
                        if m.id == self.selected_member_id:
                            selected_name = m.full_name or m.username
                            break
                    await select_interaction.response.send_message(
                        f"✅ {selected_name} sélectionné. Choisissez maintenant son statut.",
                        ephemeral=True,
                    )

                select.callback = select_callback
                self.add_item(select)

        # Instructions
        embed.add_field(
            name="📝 Instructions",
            value="1. Sélectionnez un membre dans la liste\n"
            "2. Cliquez sur son statut (Présent/Absent/Excusé)\n"
            "3. Naviguez entre les pages si nécessaire\n"
            "4. Validez l'appel quand terminé",
            inline=False,
        )

        embed.set_footer(text=f"Réunion du {meeting.date.strftime('%d/%m/%Y à %H:%M')}")

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            # Si l'interaction a déjà reçu une réponse, éditer le message original
            await interaction.message.edit(embed=embed, view=self)


async def setup(bot):
    await bot.add_cog(MeetingsCog(bot))
