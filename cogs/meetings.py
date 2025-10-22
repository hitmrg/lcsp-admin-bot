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

logger = logging.getLogger(__name__)


def is_admin():
    async def predicate(interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False
        return any(role.name in ADMIN_ROLES for role in member.roles)

    return app_commands.check(predicate)


# cog de gestion des réunions
class MeetingsCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.active_meetings = {}

    @app_commands.command(name="meeting_create", description="Créer une réunion")
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
        """Créer une nouvelle réunion avec rôles ciblés"""
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

    @app_commands.command(name="appel", description="Faire l'appel pour une réunion")
    async def start_attendance(self, interaction: discord.Interaction, reunion: str):
        """Démarrer l'appel pour une réunion (par nom)"""
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

        # Vérifier les permissions (organisateur ou admin)
        member = self.db.get_member(str(interaction.user.id))
        is_organizer = member and member.id == meeting.organizer_id
        is_admin_user = any(role.name in ADMIN_ROLES for role in interaction.user.roles)

        if not (is_organizer or is_admin_user):
            await interaction.followup.send(
                "❌ Seul l'organisateur ou un admin peut faire l'appel!"
            )
            return

        # Créer l'embed d'appel
        target_roles = meeting.get_target_roles()
        roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

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

        # Créer la vue avec les boutons
        view = AttendanceView(meeting.id, self.db, str(interaction.user.id))
        message = await interaction.followup.send(embed=embed, view=view)

        self.active_meetings[meeting.id] = message

    @app_commands.command(
        name="appel_id", description="Faire l'appel par ID (cas d'ambiguïté)"
    )
    async def start_attendance_by_id(
        self, interaction: discord.Interaction, meeting_id: int
    ):
        """Démarrer l'appel pour une réunion spécifique par ID"""
        await interaction.response.defer()

        meeting = self.db.get_meeting(meeting_id)
        if not meeting:
            await interaction.followup.send("❌ Réunion introuvable")
            return

        # Vérifier les permissions
        member = self.db.get_member(str(interaction.user.id))
        is_organizer = member and member.id == meeting.organizer_id
        is_admin_user = any(role.name in ADMIN_ROLES for role in interaction.user.roles)

        if not (is_organizer or is_admin_user):
            await interaction.followup.send(
                "❌ Seul l'organisateur ou un admin peut faire l'appel!"
            )
            return

        # Créer l'embed d'appel
        target_roles = meeting.get_target_roles()
        roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

        embed = discord.Embed(
            title=f"📢 Appel - {meeting.title}",
            description=f"**Pôles concernés:** {roles_text}\n\n"
            "Cliquez sur le bouton correspondant à votre statut",
            color=discord.Color.blue(),
            timestamp=meeting.date,
        )

        # Créer la vue avec les boutons
        view = AttendanceView(meeting.id, self.db, str(interaction.user.id))
        message = await interaction.followup.send(embed=embed, view=view)

        self.active_meetings[meeting.id] = message

    @app_commands.command(
        name="modifier_presence", description="Modifier la présence d'un membre"
    )
    @is_admin()
    async def modify_attendance(
        self,
        interaction: discord.Interaction,
        reunion: str,
        membre: discord.Member,
        statut: str,
    ):
        """Modifier la présence d'un membre après validation"""
        await interaction.response.defer(ephemeral=True)

        # Rechercher la réunion
        meetings = self.db.get_meeting_by_name(reunion)

        if not meetings:
            await interaction.followup.send(
                f"❌ Aucune réunion trouvée", ephemeral=True
            )
            return

        if len(meetings) > 1:
            await interaction.followup.send(
                "❌ Plusieurs réunions trouvées, utilisez /modifier_presence_id",
                ephemeral=True,
            )
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

        # Modifier la présence
        self.db.record_attendance(
            meeting.id, member.id, statut, modified_by=str(interaction.user.id)
        )

        await interaction.followup.send(
            f"✅ Présence modifiée: {membre.mention} → {statut}", ephemeral=True
        )

    @app_commands.command(
        name="meetings", description="Afficher les prochaines réunions"
    )
    async def list_meetings(
        self, interaction: discord.Interaction, pole: Optional[str] = None
    ):
        """Lister les prochaines réunions (optionnellement filtrées par pôle)"""
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


class AttendanceView(discord.ui.View):
    """Vue pour l'appel avec validation"""

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
        """Marquer sa présence"""
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

        self.attendees[str(interaction.user.id)] = ("present", member.id)
        await interaction.response.send_message("✅ Marqué présent", ephemeral=True)
        await self.update_display(interaction)

    @discord.ui.button(label="❌ Absent", style=discord.ButtonStyle.danger, row=0)
    async def absent(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Marquer son absence"""
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
        await interaction.response.send_message("❌ Marqué absent", ephemeral=True)
        await self.update_display(interaction)

    @discord.ui.button(label="🏥 Excusé", style=discord.ButtonStyle.secondary, row=0)
    async def excused(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Marquer son absence excusée"""
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
        await interaction.response.send_message("🏥 Marqué excusé", ephemeral=True)
        await self.update_display(interaction)

    @discord.ui.button(
        label="📝 Valider l'appel", style=discord.ButtonStyle.primary, row=1
    )
    async def validate(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Valider définitivement l'appel"""
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

        if self.validated:
            await interaction.response.send_message(
                "✅ L'appel a déjà été validé", ephemeral=True
            )
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

    async def update_display(self, interaction):
        """Mettre à jour l'affichage avec le compteur"""
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


async def setup(bot):
    await bot.add_cog(MeetingsCog(bot))
