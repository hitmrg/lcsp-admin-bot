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
        roles: Optional[
            str
        ] = "ALL",  # "ALL", "DEV", "IA", "INFRA" ou combinaison "DEV,IA"
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

        # Créer l'embed d'appel
        target_roles = meeting.get_target_roles()
        roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

        # Récupérer les membres attendus
        expected_members = self.db.get_members_by_roles(target_roles)
        # Construire une représentation en ligne (max 2000 chars)
        members_lines = []
        for m in expected_members:
            display = m.full_name or m.username
            members_lines.append(f"{display}")
        members_text = (
            ", ".join(members_lines) if members_lines else "Aucun membre attendu"
        )

        embed = discord.Embed(
            title=f"📢 Appel - {meeting.title}",
            description=f"**Pôles concernés:** {roles_text}\n\n"
            "Cliquez sur le bouton correspondant à votre statut",
            color=discord.Color.blue(),
            timestamp=meeting.date,
        )
        embed.add_field(
            name="📅 Date de la réunion",
            value=meeting.date.strftime("%d/%m/%Y à %H:%M"),
            inline=False,
        )
        embed.add_field(name="👥 Attendues", value=members_text[:1000], inline=False)

        # Créer la vue publique avec les boutons (pour que chacun puisse se marquer)
        view = AttendanceView(meeting.id, self.db, str(interaction.user.id))
        message = await interaction.followup.send(embed=embed, view=view)

        self.active_meetings[meeting.id] = message

        # Envoyer un panneau administrateur éphemère à l'initiateur permettant
        # de gérer manuellement la présence par utilisateur (paged)
        admin_view = AdminAttendanceView(
            meeting.id,
            self.db,
            str(interaction.user.id),
            public_message=message,
            cog=self,
        )
        admin_embed = discord.Embed(
            title=f"Panneau admin - {meeting.title}",
            description="Utilisez les boutons ci-dessous pour affecter un statut à chaque membre (présent/absent/excusé).",
            color=discord.Color.blurple(),
        )
        # inclure un aperçu
        if members_lines:
            admin_embed.add_field(
                name="Exemple membres",
                value=", ".join(members_lines[:10]),
                inline=False,
            )

        try:
            await interaction.followup.send(
                embed=admin_embed, view=admin_view, ephemeral=True
            )
        except Exception:
            # si l'éphemère échoue, on ignore
            pass

    # Lancer l'appel pour une réunion par ID
    @app_commands.command(
        name="appel_id", description="Faire l'appel par ID (cas d'ambiguïté)"
    )
    @app_commands.describe(
        meeting_id="ID de la réunion, récupérer au préalable après avoir fait /appel [nom réunion] (cas d'ambiguïté)"
    )
    @is_admin()
    async def start_attendance_by_id(
        self, interaction: discord.Interaction, meeting_id: int
    ):
        await interaction.response.defer()

        meeting = self.db.get_meeting(meeting_id)
        # Empêcher de relancer l'appel si déjà validé
        if not meeting:
            await interaction.followup.send("❌ Réunion introuvable")
            return

        if meeting.attendance_validated:
            await interaction.followup.send(
                "❌ L'appel pour cette réunion a déjà été validé et ne peut pas être relancé"
            )
            return
        # Créer l'embed d'appel
        target_roles = meeting.get_target_roles()
        roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

        expected_members = self.db.get_members_by_roles(target_roles)
        members_lines = [m.full_name or m.username for m in expected_members]
        members_text = (
            ", ".join(members_lines) if members_lines else "Aucun membre attendu"
        )

        embed = discord.Embed(
            title=f"📢 Appel - {meeting.title}",
            description=f"**Pôles concernés:** {roles_text}\n\n"
            "Cliquez sur le bouton correspondant à votre statut",
            color=discord.Color.blue(),
            timestamp=meeting.date,
        )
        embed.add_field(
            name="📅 Date de la réunion",
            value=meeting.date.strftime("%d/%m/%Y à %H:%M"),
            inline=False,
        )
        embed.add_field(name="👥 Attendues", value=members_text[:1000], inline=False)

        # Créer la vue publique
        view = AttendanceView(meeting.id, self.db, str(interaction.user.id))
        message = await interaction.followup.send(embed=embed, view=view)

        self.active_meetings[meeting.id] = message

        # Panneau admin éphemère
        admin_view = AdminAttendanceView(
            meeting.id,
            self.db,
            str(interaction.user.id),
            public_message=message,
            cog=self,
        )
        admin_embed = discord.Embed(
            title=f"Panneau admin - {meeting.title}",
            description="Utilisez les boutons ci-dessous pour affecter un statut à chaque membre (présent/absent/excusé).",
            color=discord.Color.blurple(),
        )
        if members_lines:
            admin_embed.add_field(
                name="Exemple membres",
                value=", ".join(members_lines[:10]),
                inline=False,
            )
        try:
            await interaction.followup.send(
                embed=admin_embed, view=admin_view, ephemeral=True
            )
        except Exception:
            pass

    # Statistiques d'une réunion
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

        meeting = stats["meeting"]
        embed = discord.Embed(
            title=f"📊 Statistiques - {meeting.title}",
            description=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}",
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

    # Modifier la présence par nom de réunion (si unique)
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
            # Afficher la liste des réunions similaires avec leur ID pour que l'admin choisisse
            embed = discord.Embed(
                title="⚠️ Plusieurs réunions trouvées",
                description="Précisez en utilisant l'ID: /modifier_presence_id [id]",
                color=discord.Color.orange(),
            )
            for meeting in meetings[:10]:
                embed.add_field(
                    name=f"#{meeting.id} - {meeting.title}",
                    value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}\nOrganisateur: <@{meeting.created_by}>",
                    inline=False,
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        meeting = meetings[0]

        # Vérifier que l'appel a été validé
        if not meeting.attendance_validated:
            await interaction.followup.send(
                "❌ L'appel n'a pas encore été validé pour cette réunion",
                ephemeral=True,
            )
            return

        # Récupérer le membre
        member = self.db.get_member(str(membre.id))
        if not member:
            await interaction.followup.send("❌ Membre non enregistré", ephemeral=True)
            return

        # Statuts valides
        valid_statuses = ["present", "absent", "excused"]
        if statut not in valid_statuses:
            await interaction.followup.send(
                f"❌ Statut invalide. Utilisez: {', '.join(valid_statuses)}",
                ephemeral=True,
            )
            return

        # Modifier la présence (utilise member.id - non discord id)
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
                    value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}\nOrganisateur: <@{meeting.created_by}>",
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

        meeting = stats["meeting"]
        embed = discord.Embed(
            title=f"📊 Statistiques - {meeting.title}",
            description=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}",
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


# Vue pour l'appel avec validation
class AttendanceView(discord.ui.View):

    def __init__(self, meeting_id, db, initiator_id):
        super().__init__(timeout=1800)  # 30 minutes
        self.meeting_id = meeting_id
        self.db = db
        self.initiator_id = initiator_id
        self.attendees = {}  # {user_id: status}
        self.validated = False

    @discord.ui.button(label="✅ Présent", style=discord.ButtonStyle.success, row=0)
    async def present(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        member = self.db.get_member(str(interaction.user.id))

        if not member:
            await interaction.response.send_message(
                "❌ Vous n'êtes pas enregistré", ephemeral=True
            )
            return

        # Vérifier que le membre est concerné par la réunion
        meeting = self.db.get_meeting(self.meeting_id)
        target_roles = meeting.get_target_roles()

        if "ALL" not in target_roles and member.role not in target_roles:
            await interaction.response.send_message(
                f"❌ Cette réunion concerne uniquement les pôles: {', '.join(target_roles)}",
                ephemeral=True,
            )
            return

        # Persister tout de suite
        self.attendees[str(interaction.user.id)] = ("present", member.id)
        try:
            self.db.record_attendance(self.meeting_id, member.id, "present")
        except Exception:
            logger.exception("Erreur en enregistrant la présence")
        await interaction.response.send_message("✅ Marqué présent", ephemeral=True)
        await self.update_display(interaction)

    @discord.ui.button(label="❌ Absent", style=discord.ButtonStyle.danger, row=0)
    async def absent(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self.db.get_member(str(interaction.user.id))

        if not member:
            await interaction.response.send_message(
                "❌ Vous n'êtes pas enregistré", ephemeral=True
            )
            return

        # Vérifier que le membre est concerné
        meeting = self.db.get_meeting(self.meeting_id)
        target_roles = meeting.get_target_roles()

        if "ALL" not in target_roles and member.role not in target_roles:
            await interaction.response.send_message(
                f"❌ Cette réunion ne vous concerne pas", ephemeral=True
            )
            return

        self.attendees[str(interaction.user.id)] = ("absent", member.id)
        try:
            self.db.record_attendance(self.meeting_id, member.id, "absent")
        except Exception:
            logger.exception("Erreur en enregistrant l'absence")
        await interaction.response.send_message("❌ Marqué absent", ephemeral=True)
        await self.update_display(interaction)

    @discord.ui.button(label="🏥 Excusé", style=discord.ButtonStyle.secondary, row=0)
    async def excused(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        member = self.db.get_member(str(interaction.user.id))

        if not member:
            await interaction.response.send_message(
                "❌ Vous n'êtes pas enregistré", ephemeral=True
            )
            return

        # Vérifier que le membre est concerné
        meeting = self.db.get_meeting(self.meeting_id)
        target_roles = meeting.get_target_roles()

        if "ALL" not in target_roles and member.role not in target_roles:
            await interaction.response.send_message(
                f"❌ Cette réunion ne vous concerne pas", ephemeral=True
            )
            return

        self.attendees[str(interaction.user.id)] = ("excused", member.id)
        try:
            self.db.record_attendance(self.meeting_id, member.id, "excused")
        except Exception:
            logger.exception("Erreur en enregistrant l'excuse")
        await interaction.response.send_message("🏥 Marqué excusé", ephemeral=True)
        await self.update_display(interaction)

    @discord.ui.button(
        label="📝 Valider l'appel", style=discord.ButtonStyle.primary, row=1
    )
    async def validate(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Vérifier les permissions
        if str(interaction.user.id) != self.initiator_id:
            member = self.db.get_member(str(interaction.user.id))
            meeting = self.db.get_meeting(self.meeting_id)
            is_organizer = member and member.id == meeting.organizer_id
            is_admin = any(role.name in ADMIN_ROLES for role in interaction.user.roles)

            if not (is_organizer or is_admin):
                await interaction.response.send_message(
                    "❌ Seul l'organisateur ou un admin peut valider l'appel!",
                    ephemeral=True,
                )
                return

        # Vérifier si la réunion a déjà été validée en base (protection contre doublons)
        meeting_obj = self.db.get_meeting(self.meeting_id)
        if meeting_obj and meeting_obj.attendance_validated:
            self.validated = True
            for item in self.children:
                item.disabled = True
            await interaction.response.send_message(
                "✅ L'appel a déjà été validé", ephemeral=True
            )
            try:
                await interaction.message.edit(view=self)
            except:
                pass
            return

        # Enregistrer toutes les présences
        for discord_id, (status, member_id) in self.attendees.items():
            self.db.record_attendance(self.meeting_id, member_id, status)

        # Marquer comme validé
        self.db.validate_attendance(self.meeting_id, str(interaction.user.id))
        self.validated = True

        # Désactiver les boutons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)

        # Message de confirmation
        meeting = self.db.get_meeting(self.meeting_id)
        embed = discord.Embed(
            title="✅ Appel validé",
            description=f"L'appel pour **{meeting.title}** a été validé",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        # Statistiques
        present = sum(
            1 for _, (status, _) in self.attendees.items() if status == "present"
        )
        absent = sum(
            1 for _, (status, _) in self.attendees.items() if status == "absent"
        )
        excused = sum(
            1 for _, (status, _) in self.attendees.items() if status == "excused"
        )

        embed.add_field(name="✅ Présents", value=present, inline=True)
        embed.add_field(name="❌ Absents", value=absent, inline=True)
        embed.add_field(name="🏥 Excusés", value=excused, inline=True)

        await interaction.followup.send(embed=embed)

    # Mettre à jour l'affichage avec le compteur
    async def update_display(self, interaction):
        meeting = self.db.get_meeting(self.meeting_id)
        target_roles = meeting.get_target_roles()

        # Compter les statuts
        present = sum(
            1 for _, (status, _) in self.attendees.items() if status == "present"
        )
        absent = sum(
            1 for _, (status, _) in self.attendees.items() if status == "absent"
        )
        excused = sum(
            1 for _, (status, _) in self.attendees.items() if status == "excused"
        )

        # Mettre à jour l'embed
        embed = interaction.message.embeds[0]

        # Ajouter/Mettre à jour le field des statistiques
        if len(embed.fields) > 1:
            embed.remove_field(1)

        stats_text = (
            f"✅ Présents: {present}\n❌ Absents: {absent}\n🏥 Excusés: {excused}"
        )
        embed.add_field(name="📊 Statut actuel", value=stats_text, inline=False)

        try:
            await interaction.message.edit(embed=embed)
        except:
            pass  # Ignorer les erreurs de mise à jour


class AdminAttendanceView(discord.ui.View):
    """Vue éphemère pour les admins/organisateurs permettant de parcourir
    la liste des membres attendus et de marquer individuellement leur statut.
    Cette vue pagine par 8 membres et propose 3 boutons de statut + navigation.
    """

    def __init__(self, meeting_id, db, initiator_id, public_message=None, cog=None):
        super().__init__(timeout=1800)
        self.meeting_id = meeting_id
        self.db = db
        self.initiator_id = initiator_id
        self.public_message = public_message
        self.cog = cog
        self.page = 0
        self.selected_member = None

        # charger membres attendus
        meeting = self.db.get_meeting(meeting_id)
        target_roles = meeting.get_target_roles() if meeting else ["ALL"]
        self.members = self.db.get_members_by_roles(target_roles)

        # Select pour choisir un membre sur la page
        class MemberSelect(discord.ui.Select):
            def __init__(inner_self, parent, options):
                super().__init__(
                    placeholder="Choisir un membre",
                    min_values=1,
                    max_values=1,
                    options=options,
                )
                inner_self.parent = parent

            async def callback(inner_self, interaction: discord.Interaction):
                # set the selected member on parent
                value = inner_self.values[0]
                # value is member.discord_id
                for m in inner_self.parent.members:
                    if m.discord_id == value:
                        inner_self.parent.selected_member = m
                        break
                await interaction.response.send_message(
                    f"Membre sélectionné: {inner_self.parent.selected_member.full_name or inner_self.parent.selected_member.username}",
                    ephemeral=True,
                )

        # initial select options
        start = 0
        block = self.members[start : start + 8]
        options = [
            discord.SelectOption(
                label=(m.full_name or m.username), value=str(m.discord_id)
            )
            for m in block
        ]
        self.member_select = MemberSelect(self, options)
        self.add_item(self.member_select)

    async def _refresh_message(self, interaction):
        # rebuild embed
        meeting = self.db.get_meeting(self.meeting_id)
        embed = discord.Embed(
            title=f"Panneau admin - {meeting.title}",
            description="Navigation: ← →. Sélectionnez un membre pour appliquer un statut.",
            color=discord.Color.blurple(),
        )
        start = self.page * 8
        block = self.members[start : start + 8]
        for m in block:
            display = m.full_name or m.username
            embed.add_field(
                name=f"{display}",
                value=f"Discord: <@{m.discord_id}> | Role: {m.role}",
                inline=False,
            )

        # Mettre à jour les options du select
        try:
            options = [
                discord.SelectOption(
                    label=(m.full_name or m.username), value=str(m.discord_id)
                )
                for m in block
            ]
            self.member_select.options = options
        except Exception:
            logger.exception("Erreur en mettant à jour le select de l'admin panel")

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception:
            try:
                await interaction.followup.send(embed=embed, view=self, ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="←", style=discord.ButtonStyle.secondary, row=0)
    async def prev_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page > 0:
            self.page -= 1
        await self._refresh_message(interaction)

    @discord.ui.button(label="→", style=discord.ButtonStyle.secondary, row=0)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if (self.page + 1) * 8 < len(self.members):
            self.page += 1
        await self._refresh_message(interaction)

    @discord.ui.button(label="Présent", style=discord.ButtonStyle.success, row=1)
    async def mark_present(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # marque tous les membres de la page comme présent
        start = self.page * 8
        block = self.members[start : start + 8]
        for m in block:
            try:
                self.db.record_attendance(
                    self.meeting_id,
                    m.id,
                    "present",
                    modified_by=str(interaction.user.id),
                )
            except Exception:
                logger.exception("Erreur en marquant présent via admin panel")
        await interaction.response.send_message(
            "✅ Page marquée présente", ephemeral=True
        )
        # Mettre à jour le message public si nécessaire
        if self.public_message:
            try:
                await self.public_message.edit(
                    view=(
                        self.cog.active_meetings.get(self.meeting_id).view
                        if self.cog and self.meeting_id in self.cog.active_meetings
                        else None
                    )
                )
            except Exception:
                pass
        await self._refresh_message(interaction)

    @discord.ui.button(label="Absent", style=discord.ButtonStyle.danger, row=1)
    async def mark_absent(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        start = self.page * 8
        block = self.members[start : start + 8]
        for m in block:
            try:
                self.db.record_attendance(
                    self.meeting_id,
                    m.id,
                    "absent",
                    modified_by=str(interaction.user.id),
                )
            except Exception:
                logger.exception("Erreur en marquant absent via admin panel")
        await interaction.response.send_message(
            "❌ Page marquée absente", ephemeral=True
        )
        await self._refresh_message(interaction)

    @discord.ui.button(label="Excusé", style=discord.ButtonStyle.secondary, row=1)
    async def mark_excused(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        start = self.page * 8
        block = self.members[start : start + 8]
        for m in block:
            try:
                self.db.record_attendance(
                    self.meeting_id,
                    m.id,
                    "excused",
                    modified_by=str(interaction.user.id),
                )
            except Exception:
                logger.exception("Erreur en marquant excusé via admin panel")
        await interaction.response.send_message(
            "🏥 Page marquée excusée", ephemeral=True
        )
        await self._refresh_message(interaction)


async def setup(bot):
    await bot.add_cog(MeetingsCog(bot))
