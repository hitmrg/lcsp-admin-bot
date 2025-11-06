import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin
from views.createAttendance import create_attendance_view

logger = logging.getLogger(__name__)


class AppelID(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

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
        await self.create_attendance_view(interaction, meeting)

        logger.info(
            f"🟢 Appel lancé pour la réunion ID {meeting_id} par {interaction.user} ({interaction.user.id})"
        )

async def setup(bot):
    await bot.add_cog(AppelID(bot))