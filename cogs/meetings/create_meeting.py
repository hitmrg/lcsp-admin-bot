import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


# cog pour la création de réunions
class CreateMeeting(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Création d'une réunion
    @app_commands.command(name="meeting_create", description="Créer une réunion")
    @app_commands.describe(
        titre="Titre de la réunion",
        date="Date de la réunion (JJ/MM/AAAA)",
        heure="Heure de la réunion (HH:MM)",
        roles='Rôles ciblés ("ALL", "DEV", "IA", "INFRA" ou combinaison "DEV,IA")',
        description="Description de la réunion (optionnel)",
    )
    @is_admin()
    async def create_meeting(
        self,
        interaction: discord.Interaction,
        titre: str,
        date: str,
        heure: str,
        roles: Optional[str] = "ALL",
        description: Optional[str] = None,
    ):
        await interaction.response.defer()

        # Parser la date et heure
        try:
            datetime_str = f"{date} {heure}"
            meeting_date = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
        except ValueError:
            await interaction.followup.send(
                "❌ Format invalide!\nDate: JJ/MM/AAAA\nHeure: HH:MM"
            )
            return

        # Vérifier que la date est dans le futur
        if meeting_date <= datetime.now():
            await interaction.followup.send("❌ La réunion doit être dans le futur!")
            return

        # Parser les rôles ciblés
        if roles.upper() == "ALL":
            target_roles = ["ALL"]
        else:
            target_roles = [r.strip().upper() for r in roles.split(",")]
            valid_roles = ["DEV", "IA", "INFRA"]
            for role in target_roles:
                if role not in valid_roles:
                    await interaction.followup.send(
                        f"❌ Rôle invalide: {role}\nRôles valides: {', '.join(valid_roles)}"
                    )
                    return

        # Récupérer l'organisateur
        organizer = self.db.get_member(str(interaction.user.id))
        if not organizer:
            await interaction.followup.send(
                "❌ Vous devez être enregistré comme membre pour créer une réunion"
            )
            return

        # Créer la réunion
        meeting = self.db.create_meeting(
            title=titre,
            date=meeting_date,
            description=description,
            created_by=str(interaction.user.id),
            organizer_id=organizer.id,
            target_roles=target_roles,
        )

        # Créer l'embed de confirmation
        embed = discord.Embed(
            title="✅ Réunion créée",
            color=discord.Color.green(),
            timestamp=meeting_date,
        )
        embed.add_field(name="📝 Titre", value=titre, inline=False)
        embed.add_field(name="📅 Date", value=date, inline=True)
        embed.add_field(name="⏰ Heure", value=heure, inline=True)
        embed.add_field(
            name="👥 Pôles concernés",
            value="Tous" if "ALL" in target_roles else ", ".join(target_roles),
            inline=True,
        )
        if description:
            embed.add_field(name="📋 Description", value=description, inline=False)
        embed.set_footer(text=f"Organisée par {interaction.user.display_name}")

        # Mentionner les rôles concernés
        mentions = []
        if "ALL" in target_roles:
            mentions.append("@everyone")
        else:
            for role_name in target_roles:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    mentions.append(role.mention)

        await interaction.followup.send(
            content=" ".join(mentions) if mentions else None, embed=embed
        )

        # Log de l'action
        logger.info(
            f"Réunion créée: {titre} par {interaction.user} pour rôles {', '.join(target_roles)}"
        )

async def setup(bot):
    await bot.add_cog(CreateMeeting(bot))