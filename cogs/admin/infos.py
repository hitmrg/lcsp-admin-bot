import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from .is_admin import is_admin

logger = logging.getLogger(__name__)


# Cog d'administration
class Informations(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()    

    # Commande d'informations sur le serveur
    @app_commands.command(name="info", description="Informations sur le serveur")
    @is_admin()
    async def server_info(self, interaction: discord.Interaction):
        await interaction.response.defer()

        guild = interaction.guild

        # Créer l'embed
        embed = discord.Embed(
            title=f"ℹ️ Informations - {guild.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Statistiques générales
        embed.add_field(
            name="📊 Statistiques",
            value=f"Membres: {guild.member_count}\n"
            f"Rôles: {len(guild.roles)}\n"
            f"Canaux: {len(guild.channels)}",
            inline=True,
        )

        # Rôles techniques
        tech_roles = ["DEV", "IA", "INFRA"]
        role_counts = {}
        for role_name in tech_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                role_counts[role_name] = len(role.members)

        if role_counts:
            embed.add_field(
                name="👥 Répartition des pôles",
                value="\n".join(
                    f"{name}: {count}" for name, count in role_counts.items()
                ),
                inline=True,
            )

        # Informations de création
        embed.add_field(
            name="📅 Création", value=guild.created_at.strftime("%d/%m/%Y"), inline=True
        )

        # Propriétaire
        embed.add_field(
            name="👑 Propriétaire",
            value=guild.owner.mention if guild.owner else "Non défini",
            inline=True,
        )

        await interaction.followup.send(embed=embed)

# Fonction de setup du cog
async def setup(bot):
    await bot.add_cog(Informations(bot))