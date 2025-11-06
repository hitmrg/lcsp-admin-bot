import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from .is_admin import is_admin

logger = logging.getLogger(__name__)


# Cog d'administration
class Clear(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Commande de suppression de messages
    @app_commands.command(name="clear", description="Supprimer des messages")
    @app_commands.describe(
        nombre="Nombre de messages à supprimer (1-100)",
        user="Supprimer uniquement les messages d'un utilisateur spécifique (optionnel)",
    )
    @is_admin()
    async def clear(
        self,
        interaction: discord.Interaction,
        nombre: int,
        user: Optional[discord.Member] = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if nombre < 1 or nombre > 100:
            await interaction.followup.send(
                "❌ Le nombre doit être entre 1 et 100", ephemeral=True
            )
            return

        # Supprimer les messages
        deleted = []
        if user:
            # Supprimer uniquement les messages de l'utilisateur spécifié
            def check(m):
                return m.author == user

            deleted = await interaction.channel.purge(limit=nombre, check=check)
        else:
            deleted = await interaction.channel.purge(limit=nombre)

        await interaction.followup.send(
            f"✅ {len(deleted)} messages supprimés", ephemeral=True
        )

# Fonction de setup du cog
async def setup(bot):
    await bot.add_cog(Clear(bot))