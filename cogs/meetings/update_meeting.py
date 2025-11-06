import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class UpdateMeeting(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.active_meetings = {}

    # Commande pour modifier une réunion par le nom
    @app_commands.command(
        name="meeting_update", description="Modifier une réunion par nom"
    )
    @app_commands.describe(
        reunion="Nom ou partie du nom de la réunion",
        titre="Nouveau titre de la réunion",
        date="Nouvelle date de la réunion (JJ/MM/AAAA)",
        heure="Nouvelle heure de la réunion (HH:MM)",
        roles='Nouveaux rôles ciblés ("ALL", "DEV", "IA", "INFRA" ou combinaison "DEV,IA")',
        description="Nouvelle description de la réunion (optionnel)",
    )
    @is_admin()
    async def update_meeting(
        self,
        interaction: discord.Interaction,
        reunion: str,
        titre: str,
        date: str,
        heure: str,
        roles: Optional[str] = "ALL",
        description: Optional[str] = None,
    ):
        await interaction.response.defer()

        if self.db.update_meeting_by_name(
            reunion, titre, date, heure, roles, description
        ):
            await interaction.followup.send(f"✅ Réunion '{reunion}' modifiée")
        else:
            await interaction.followup.send(f"❌ Réunion non trouvée", ephemeral=True)

        logger.info(
            f"Réunion modifiée par {interaction.user} : {reunion} -> {titre}, {date} {heure}, rôles: {roles}"
        )

async def setup(bot):
    await bot.add_cog(UpdateMeeting(bot))