import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class ModifyPresenceID(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

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

        logger.info(
            f"✏️ Présence modifiée par {interaction.user} pour la réunion {meeting.id}: {membre} → {statut}"
        )

async def setup(bot):
    await bot.add_cog(ModifyPresenceID(bot))