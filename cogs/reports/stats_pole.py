import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from database import Database
from models import MemberStatus

logger = logging.getLogger(__name__)


class PoleStats(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Statistiques par pôle
    @app_commands.command(
        name="stats_pole", description="Statistiques détaillées d'un pôle"
    )
    @app_commands.describe(
        pole="Pôle à analyser (DEV, IA, INFRA)",
        jours="Nombre de jours à analyser (ex: 30)",
    )
    async def stats_pole(
        self,
        interaction: discord.Interaction,
        pole: str,  # DEV, IA, INFRA
        jours: Optional[int] = 30,
    ):
        await interaction.response.defer()

        pole = pole.upper()
        if pole not in ["DEV", "IA", "INFRA"]:
            await interaction.followup.send(
                "❌ Pôle invalide. Utilisez: DEV, IA, ou INFRA"
            )
            return

        # Récupérer les stats du pôle
        stats = self.db.get_role_stats(pole, days=jours)

        # Icônes et couleurs
        config = {
            "DEV": {"icon": "💻", "color": discord.Color.blue()},
            "IA": {"icon": "🤖", "color": discord.Color.purple()},
            "INFRA": {"icon": "🛠️", "color": discord.Color.green()},
        }

        pole_config = config[pole]

        # Créer l'embed
        embed = discord.Embed(
            title=f"{pole_config['icon']} Statistiques Pôle {pole}",
            description=f"Période: {jours} derniers jours",
            color=pole_config["color"],
            timestamp=discord.utils.utcnow(),
        )

        # Vue d'ensemble du pôle
        embed.add_field(
            name="📊 Vue d'ensemble",
            value=f"**Membres actifs:** {stats['members_count']}\n"
            f"**Réunions complétées:** {stats['total_meetings']}\n"
            f"**Réunions à venir:** {stats.get('upcoming_meetings', 0)}\n"
            f"**Taux de participation moyen:** {stats['avg_attendance_rate']:.1f}%",
            inline=False,
        )

        # Graphique de participation (représentation textuelle)
        if stats["avg_attendance_rate"] > 0:
            bar_length = int(stats["avg_attendance_rate"] / 5)  # Max 20 caractères
            bar = "█" * bar_length + "░" * (20 - bar_length)
            embed.add_field(
                name="📈 Taux de participation",
                value=f"`{bar}` {stats['avg_attendance_rate']:.0f}%",
                inline=False,
            )

        # Top membres du pôle
        if stats["top_members"]:
            top_text = ""
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

            for i, member in enumerate(stats["top_members"]):
                medal = medals[i] if i < len(medals) else f"{i+1}."
                top_text += f"{medal} **{member['member']}**\n"
                top_text += (
                    f"   → {member['rate']:.0f}% - {member['attended']} présences\n"
                )

            embed.add_field(name="🏆 Top membres du pôle", value=top_text, inline=False)

        # Liste complète des membres
        members = self.db.get_all_members(role=pole, status=MemberStatus.ACTIVE)
        if members:
            members_list = []
            for member in members:
                member_stats = self.db.get_member_stats(member.id, days=jours)
                status_icon = (
                    "✅"
                    if member_stats["rate"] >= 70
                    else "⚠️" if member_stats["rate"] >= 50 else "❌"
                )
                members_list.append(
                    f"{status_icon} {member.full_name or member.username}"
                )

            # Diviser en colonnes si trop de membres
            if len(members_list) <= 10:
                embed.add_field(
                    name="👥 Tous les membres",
                    value="\n".join(members_list),
                    inline=False,
                )
            else:
                mid = len(members_list) // 2
                embed.add_field(
                    name="👥 Membres (1/2)",
                    value="\n".join(members_list[:mid]),
                    inline=True,
                )
                embed.add_field(
                    name="👥 Membres (2/2)",
                    value="\n".join(members_list[mid:]),
                    inline=True,
                )

        # Prochaines réunions du pôle
        upcoming = self.db.get_upcoming_meetings(limit=3, role=pole)
        if upcoming:
            meetings_text = ""
            for meeting in upcoming:
                meetings_text += f"📅 **{meeting.title}**\n"
                meetings_text += f"   {meeting.date.strftime('%d/%m à %H:%M')}\n"

            embed.add_field(
                name="📅 Prochaines réunions", value=meetings_text, inline=False
            )

        embed.set_footer(text=f"LCSP - Pôle {pole}")

        await interaction.followup.send(embed=embed)

        logger.info(
            f"📊 Statistiques pôle {pole} générées par {interaction.user} pour les {jours} derniers jours."
        )

async def setup(bot):
    await bot.add_cog(PoleStats(bot))