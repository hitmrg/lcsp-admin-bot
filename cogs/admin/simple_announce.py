import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from .is_admin import is_admin

logger = logging.getLogger(__name__)


# Cog d'administration
class SimpleAnnounce(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Commande d'annonce simple
    @app_commands.command(
        name="announce_simple",
        description="Faire une annonce simple (titre + message, couleur bleue)",
    )
    @app_commands.describe(
        ping="Mentionner tout le monde (oui/non)",
    )
    @is_admin()
    async def announce_simple(
        self,
        interaction: discord.Interaction,
        titre: str,
        message: str,
        ping: Optional[bool] = False,
    ):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=f"📢 {titre}",
            description=message,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(
            text=f"LCSP - {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )

        content = "@everyone" if ping else None
        await interaction.channel.send(content=content, embed=embed)
        await interaction.followup.send("✅ Annonce envoyée", ephemeral=True)

# Fonction de setup du cog
async def setup(bot):
    await bot.add_cog(SimpleAnnounce(bot))