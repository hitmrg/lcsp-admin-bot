import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class DeleteMeetingID(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Commande pour supprimer un meeting par le nom
    @app_commands.command(
        name="meeting_delete_id", description="Supprimer une réunion par ID"
    )
    @app_commands.describe(meeting_id="Nom ou partie du nom de la réunion")
    @is_admin()
    async def delete_meeting_id(
        self, interaction: discord.Interaction, meeting_id: int
    ):
        await interaction.response.defer()

        meeting = self.db.get_meeting(meeting_id)
        if not meeting:
            await interaction.followup.send("❌ Réunion introuvable")
            return

        # Supprime la réunion
        await self.delete_meeting_id(meeting_id)

        await interaction.followup.send(f"✅ Réunion avec ID {meeting_id} supprimée")

        # Log de l'action
        logger.info(
            f"🗑️ Réunion supprimée par {interaction.user} (ID: {meeting_id})"
        )

async def setup(bot):
    await bot.add_cog(DeleteMeetingID(bot))