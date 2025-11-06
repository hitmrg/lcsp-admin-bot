import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database

logger = logging.getLogger(__name__)

class ResearchMember(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Rechercher un membre
    @app_commands.command(name="membre_search", description="Rechercher un membre")
    @app_commands.describe(recherche="Nom, username ou email à rechercher")
    async def search_member(self, interaction: discord.Interaction, recherche: str):
        await interaction.response.defer()

        members = self.db.get_all_members()

        # Filtrer les membres
        results = []
        search_lower = recherche.lower()
        for member in members:
            if (
                search_lower in (member.full_name or "").lower()
                or search_lower in member.username.lower()
                or search_lower in (member.email or "").lower()
            ):
                results.append(member)

        if not results:
            await interaction.followup.send(
                f"❌ Aucun membre trouvé pour '{recherche}'"
            )
            return

        # Créer l'embed des résultats
        embed = discord.Embed(
            title=f"🔍 Résultats de recherche",
            description=f"Recherche: **{recherche}**\n{len(results)} résultat(s)",
            color=discord.Color.blue(),
        )

        for member in results[:10]:  # Limiter à 10 résultats
            # Récupérer l'utilisateur Discord
            discord_user = interaction.guild.get_member(int(member.discord_id))
            user_mention = (
                f"<@{member.discord_id}>" if discord_user else "Utilisateur introuvable"
            )

            embed.add_field(
                name=member.full_name or member.username,
                value=f"Discord: {user_mention}\n"
                f"Pôle: {member.role or 'Non défini'}\n"
                f"Statut: {member.status.value}",
                inline=True,
            )

        if len(results) > 10:
            embed.set_footer(text=f"... et {len(results) - 10} autres résultats")

        await interaction.followup.send(embed=embed)

        logger.info(f"🔍 Recherche de membre par {interaction}")

async def setup(bot):
    await bot.add_cog(ResearchMember(bot))