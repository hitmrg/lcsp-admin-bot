import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database

logger = logging.getLogger(__name__)


class InfoMember(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

# Voir les informations d'un membre
    @app_commands.command(
        name="membre_info", description="Informations détaillées d'un membre"
    )
    @app_commands.describe(
        user="Utilisateur Discord du membre (laisser vide pour vous-même)"
    )
    async def member_info(
        self, interaction: discord.Interaction, user: Optional[discord.Member] = None
    ):
        await interaction.response.defer()

        target = user or interaction.user
        member = self.db.get_member(str(target.id))

        if not member:
            await interaction.followup.send(f"❌ {target.mention} n'est pas enregistré")
            return

        # Calculer les stats
        stats = self.db.get_member_stats(member.id)

        # Récupérer les réunions à venir
        upcoming_meetings = self.db.get_member_upcoming_meetings(member.id)

        # Créer l'embed
        embed = discord.Embed(title=f"👤 Fiche membre LCSP", color=discord.Color.blue())
        embed.set_thumbnail(url=target.display_avatar.url)

        # Informations principales
        embed.add_field(
            name="📋 Identité",
            value=f"**Nom:** {member.full_name or 'Non renseigné'}\n"
            f"**Discord:** {target.mention}\n"
            f"**Username:** {member.username}",
            inline=False,
        )

        embed.add_field(
            name="💼 Professionnel",
            value=f"**Pôle:** {member.role or 'Non défini'}\n"
            f"**Spécialisation:** {member.specialization or 'Non renseignée'}\n"
            f"**Email:** {member.email or 'Non renseigné'}",
            inline=False,
        )

        embed.add_field(
            name="📊 Statistiques (30 derniers jours)",
            value=f"**Statut:** {member.status.value}\n"
            f"**Membre depuis:** {member.joined_at.strftime('%d/%m/%Y')}\n"
            f"**Dernière activité:** {member.last_active.strftime('%d/%m/%Y')}\n"
            f"**Présence:** {stats['rate']:.1f}% ({stats['attended']}/{stats['total']} réunions)\n"
            f"**Réunions complétées:** {stats.get('completed', stats['total'])}\n"
            f"**Réunions à venir:** {stats.get('upcoming', 0)}",
            inline=False,
        )

        # Ajouter les prochaines réunions si il y en a
        if upcoming_meetings:
            meetings_text = ""
            for i, meeting in enumerate(upcoming_meetings[:5], 1):  # Limiter à 5
                meetings_text += f"{i}. **{meeting.title}**\n"
                meetings_text += f"   📅 {meeting.date.strftime('%d/%m/%Y à %H:%M')}\n"
            
            embed.add_field(
                name="📅 Prochaines réunions",
                value=meetings_text,
                inline=False,
            )

        embed.set_footer(text=f"ID Membre: {member.id}")

        await interaction.followup.send(embed=embed)

        logger.info(f"ℹ️ Infos membre demandées pour {target} par {interaction.user}")

async def setup(bot):
    await bot.add_cog(InfoMember(bot))