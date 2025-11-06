import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database

logger = logging.getLogger(__name__)


class MeetingStatsID(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Statistiques d'une réunion par ID
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

        meeting_data = stats["meeting_data"]
        embed = discord.Embed(
            title=f"📊 Statistiques - {meeting_data['title']}",
            description=f"Date: {meeting_data['date'].strftime('%d/%m/%Y %H:%M')}",
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

        logger.info(
            f"📊 Statistiques réunion ID {meeting_id} demandées par {interaction.user}"
        )

async def setup(bot):
    await bot.add_cog(MeetingStatsID(bot))