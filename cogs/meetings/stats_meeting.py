import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database

logger = logging.getLogger(__name__)


class MeetingStats(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Statistiques d'une réunion par nom
    @app_commands.command(
        name="meeting_stats",
        description="Voir les statistiques d'une réunion (nom partiel)",
    )
    @app_commands.describe(reunion="Nom ou partie du nom de la réunion")
    async def meeting_stats(self, interaction: discord.Interaction, reunion: str):
        await interaction.response.defer()

        meetings = self.db.get_meeting_by_name(reunion)
        if not meetings:
            await interaction.followup.send(
                f"❌ Aucune réunion trouvée avec le nom '{reunion}'", ephemeral=True
            )
            return

        if len(meetings) > 1:
            embed = discord.Embed(
                title="⚠️ Plusieurs réunions trouvées",
                description="Veuillez préciser en utilisant l'ID:",
                color=discord.Color.orange(),
            )
            for meeting in meetings[:5]:
                embed.add_field(
                    name=f"#{meeting.id} - {meeting.title}",
                    value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}\n"
                    f"Organisateur: <@{meeting.created_by}>",
                    inline=False,
                )
            embed.set_footer(text="Utilisez: /meeting_stats_id [id]")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        meeting = meetings[0]
        stats = self.db.get_meeting_stats(meeting.id)
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

        logger.info(f"📊 Statistiques réunion '{meeting_data['title']}' consultées par {interaction.user}")

async def setup(bot):
    await bot.add_cog(MeetingStats(bot))