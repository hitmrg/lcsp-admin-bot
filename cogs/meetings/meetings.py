import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database

logger = logging.getLogger(__name__)


class Meetings(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Afficher les prochaines réunions
    @app_commands.command(
        name="meetings", description="Afficher les prochaines réunions"
    )
    @app_commands.describe(pole="Filtrer par pôle (DEV, IA, INFRA) - optionnel")
    async def list_meetings(
        self, interaction: discord.Interaction, pole: Optional[str] = None
    ):
        await interaction.response.defer()

        meetings = self.db.get_upcoming_meetings(
            limit=10, role=pole.upper() if pole else None
        )

        if not meetings:
            msg = "Aucune réunion prévue"
            if pole:
                msg += f" pour le pôle {pole.upper()}"
            await interaction.followup.send(msg)
            return

        # Créer l'embed
        title = "📅 Prochaines réunions"
        if pole:
            title += f" - Pôle {pole.upper()}"

        embed = discord.Embed(
            title=title, color=discord.Color.blue(), timestamp=discord.utils.utcnow()
        )

        for meeting in meetings:
            target_roles = meeting.get_target_roles()
            roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

            field_value = f"📅 {meeting.date.strftime('%d/%m/%Y à %H:%M')}\n"
            field_value += f"👥 Pôles: {roles_text}\n"
            if meeting.description:
                field_value += f"📝 {meeting.description[:100]}..."

            embed.add_field(name=f"{meeting.title}", value=field_value, inline=False)

        await interaction.followup.send(embed=embed)

        logger.info(
            f"📅 {interaction.user} a consulté les réunions"
        )

async def setup(bot):
    await bot.add_cog(Meetings(bot))