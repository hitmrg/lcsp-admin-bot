import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from database import Database
from models import MemberStatus

logger = logging.getLogger(__name__)

class LaboStats(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Statistiques générales
    @app_commands.command(name="stats", description="Statistiques générales du LCSP")
    @app_commands.describe(jours="Nombre de jours à analyser (ex: 30)")
    async def stats(self, interaction: discord.Interaction, jours: Optional[int] = 30):
        await interaction.response.defer()

        # Récupérer les stats globales
        global_stats = self.db.get_global_stats(days=jours)

        # Récupérer les données par pôle
        poles = ["DEV", "IA", "INFRA"]
        pole_stats = {}
        for pole in poles:
            pole_stats[pole] = self.db.get_role_stats(pole, days=jours)

        # Créer l'embed principal
        embed = discord.Embed(
            title=f"📊 Statistiques LCSP - {jours} derniers jours",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        # Vue d'ensemble
        embed.add_field(
            name="🏛️ Vue d'ensemble",
            value=f"**Membres actifs:** {global_stats['active_members']}\n"
            f"**Réunions complétées:** {global_stats['total_meetings']}\n"
            f"**Réunions à venir:** {global_stats.get('upcoming_meetings', 0)}\n"
            f"**Taux de participation global:** {global_stats['global_attendance_rate']:.1f}%",
            inline=False,
        )

        # Séparateur visuel
        embed.add_field(name="\u200b", value="─" * 30, inline=False)

        # Statistiques par pôle
        for pole, stats in pole_stats.items():
            # Icônes par pôle
            icons = {"DEV": "💻", "IA": "🤖", "INFRA": "🛠️"}
            icon = icons.get(pole, "📊")

            value = f"**Membres:** {stats['members_count']}\n"
            value += f"**Taux moyen:** {stats['avg_attendance_rate']:.1f}%\n"
            value += f"**Complétées:** {stats['total_meetings']}\n"
            value += f"**À venir:** {stats.get('upcoming_meetings', 0)}"

            embed.add_field(name=f"{icon} Pôle {pole}", value=value, inline=True)

        # Top membres global (tous pôles confondus)
        all_members = self.db.get_all_members(status=MemberStatus.ACTIVE)
        member_rates = []

        for member in all_members:
            stats = self.db.get_member_stats(member.id, days=jours)
            if stats["total"] > 0:  # Seulement ceux qui ont eu des réunions
                member_rates.append(
                    {
                        "name": member.full_name or member.username,
                        "role": member.role,
                        "rate": stats["rate"],
                        "attended": stats["attended"],
                        "total": stats["total"],
                        "upcoming": stats.get("upcoming", 0),
                    }
                )

        # Trier par taux de présence
        member_rates.sort(key=lambda x: x["rate"], reverse=True)

        # Séparateur
        embed.add_field(name="\u200b", value="─" * 30, inline=False)

        # Top 5 membres
        if member_rates:
            top_text = ""
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

            for i, member in enumerate(member_rates[:5]):
                medal = medals[i] if i < len(medals) else f"{i+1}."
                top_text += f"{medal} **{member['name']}** ({member['role']})\n"
                top_text += f"   → {member['rate']:.0f}% ({member['attended']}/{member['total']} réunions)\n"

            embed.add_field(
                name="🏆 Top 5 - Meilleure assiduité", value=top_text, inline=False
            )

        # Membres à risque (taux < 50%)
        at_risk = [m for m in member_rates if m["rate"] < 50 and m["total"] >= 2]
        if at_risk:
            risk_text = ""
            for member in at_risk[:5]:
                risk_text += f"⚠️ **{member['name']}** - {member['rate']:.0f}%\n"

            embed.add_field(name="⚠️ Attention requise", value=risk_text, inline=False)

        embed.set_footer(text="Laboratoire de Cybersécurité SUPINFO Paris")

        await interaction.followup.send(embed=embed)

        logger.info(
            f"🟢 Statistiques générales générées par {interaction.user}")

async def setup(bot):
    await bot.add_cog(LaboStats(bot))