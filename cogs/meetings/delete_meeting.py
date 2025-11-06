import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class DeleteMeeting(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Commande pour supprimer un meeting par le nom
    @app_commands.command(
        name="meeting_delete", description="Supprimer une réunion par nom"
    )
    @app_commands.describe(reunion="Nom ou partie du nom de la réunion")
    @is_admin()
    async def delete_meeting(self, interaction: discord.Interaction, reunion: str):
        await interaction.response.defer()

        if self.db.delete_meeting(str(reunion)):
            await interaction.followup.send(f"✅ Réunion '{reunion}' supprimée")
        else:
            await interaction.followup.send(f"❌ Meeting non trouvé", ephemeral=True)

        # Log de l'action
        logger.info(f"🗑️ Réunion '{reunion}' supprimée par {interaction.user}")

async def setup(bot):
    await bot.add_cog(DeleteMeeting(bot))