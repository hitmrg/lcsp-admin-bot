import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class UpdateMeetingID(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        
    # Commande pour modifier une réunion par ID
    @app_commands.command(
        name="meeting_update_id", description="Modifier une réunion par ID"
    )
    @app_commands.describe(
        meeting_id="ID de la réunion",
        titre="Nouveau titre de la réunion",
        date="Nouvelle date de la réunion (JJ/MM/AAAA)",
        heure="Nouvelle heure de la réunion (HH:MM)",
        roles='Nouveaux rôles ciblés ("ALL", "DEV", "IA", "INFRA" ou combinaison "DEV,IA")',
        description="Nouvelle description de la réunion (optionnel)",
    )
    @is_admin()
    async def update_meeting_by_id(
        self,
        interaction: discord.Interaction,
        meeting_id: int,
        titre: str,
        date: str,
        heure: str,
        roles: Optional[str] = "ALL",
        description: Optional[str] = None,
    ):
        await interaction.response.defer()

        meeting = self.db.get_meeting(meeting_id)
        if not meeting:
            await interaction.followup.send("❌ Réunion introuvable", ephemeral=True)
            return

        if self.db.update_meeting_by_id(
            meeting_id, titre, date, heure, roles, description
        ):
            await interaction.followup.send(f"✅ Réunion ID '{meeting_id}' modifiée")
        else:
            await interaction.followup.send(
                f"❌ Erreur lors de la modification", ephemeral=True
            )
        
        logger.info(
            f"Réunion modifiée par {interaction.user} : ID {meeting_id} -> {titre}, {date} {heure}, rôles: {roles}"
        )

async def setup(bot):
    await bot.add_cog(UpdateMeetingID(bot))