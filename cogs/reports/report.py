import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime, timedelta
import logging
import io
import csv
from database import Database
from models import MemberStatus

logger = logging.getLogger(__name__)

class Report(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Rapport d'activité complet
    @app_commands.command(name="rapport", description="Rapport d'activité détaillé")
    @app_commands.describe(
        jours="Nombre de jours à analyser (ex: 30)",
        format="Format du rapport (embed ou file)",
    )
    async def report(
        self,
        interaction: discord.Interaction,
        jours: Optional[int] = 30,
        format: Optional[str] = "embed",  # embed ou file
    ):
        await interaction.response.defer()

        # Récupérer toutes les données
        global_stats = self.db.get_global_stats(days=jours)
        members = self.db.get_all_members(status=MemberStatus.ACTIVE)

        if format == "file":
            # Générer un rapport CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # En-têtes
            writer.writerow(
                [
                    "Nom",
                    "Username",
                    "Email",
                    "Pôle",
                    "Statut",
                    "Réunions Total",
                    "Présences",
                    "Taux (%)",
                    "Réunions À Venir",
                    "Membre Depuis",
                    "Dernière Activité",
                ]
            )

            # Données
            for member in members:
                stats = self.db.get_member_stats(member.id, days=jours)
                writer.writerow(
                    [
                        member.full_name or "",
                        member.username,
                        member.email or "",
                        member.role or "",
                        member.status.value,
                        stats["total"],
                        stats["attended"],
                        f"{stats['rate']:.1f}",
                        stats.get("upcoming", 0),
                        member.joined_at.strftime("%d/%m/%Y"),
                        member.last_active.strftime("%d/%m/%Y"),
                    ]
                )

            # Créer le fichier
            csv_data = output.getvalue()
            file = discord.File(
                io.BytesIO(csv_data.encode("utf-8")),
                filename=f"rapport_lcsp_{datetime.now().strftime('%Y%m%d')}.csv",
            )

            await interaction.followup.send(
                f"📊 Rapport d'activité LCSP - {jours} jours", file=file
            )

        else:
            # Format embed
            embed = discord.Embed(
                title=f"📋 Rapport d'activité LCSP - {jours} jours",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow(),
            )

            # Résumé exécutif
            embed.add_field(
                name="📈 Résumé exécutif",
                value=f"**Période analysée:** {jours} jours\n"
                f"**Membres actifs:** {global_stats['active_members']}\n"
                f"**Réunions complétées:** {global_stats['total_meetings']}\n"
                f"**Réunions à venir:** {global_stats.get('upcoming_meetings', 0)}\n"
                f"**Taux participation global:** {global_stats['global_attendance_rate']:.1f}%",
                inline=False,
            )

            # Analyse par pôle
            poles_analysis = ""
            for pole in ["DEV", "IA", "INFRA"]:
                pole_stats = self.db.get_role_stats(pole, days=jours)
                if pole_stats["members_count"] > 0:
                    trend = (
                        "📈"
                        if pole_stats["avg_attendance_rate"] >= 70
                        else "📊" if pole_stats["avg_attendance_rate"] >= 50 else "📉"
                    )
                    poles_analysis += f"{trend} **{pole}:** {pole_stats['avg_attendance_rate']:.0f}% ({pole_stats['members_count']} membres)\n"

            embed.add_field(
                name="🏛️ Performance par pôle",
                value=poles_analysis or "Aucune donnée",
                inline=False,
            )

            # Identifier les membres inactifs
            inactive = []
            threshold = datetime.utcnow() - timedelta(days=14)
            for member in members:
                if member.last_active < threshold:
                    inactive.append(
                        f"{member.full_name or member.username} ({member.role})"
                    )

            if inactive:
                embed.add_field(
                    name=f"⚠️ Membres inactifs (+14 jours)",
                    value="\n".join(inactive[:5]),
                    inline=False,
                )
                if len(inactive) > 5:
                    embed.set_footer(
                        text=f"... et {len(inactive) - 5} autres membres inactifs"
                    )

            # Recommandations
            recommendations = []
            if global_stats["global_attendance_rate"] < 50:
                recommendations.append(
                    "🔴 Taux de participation critique - Action urgente requise"
                )
            elif global_stats["global_attendance_rate"] < 70:
                recommendations.append("🟡 Taux de participation à améliorer")
            else:
                recommendations.append("🟢 Bon taux de participation - À maintenir")

            if inactive:
                recommendations.append(
                    f"📧 Contacter les {len(inactive)} membres inactifs"
                )

            embed.add_field(
                name="💡 Recommandations",
                value="\n".join(recommendations),
                inline=False,
            )

            await interaction.followup.send(embed=embed)

            logger.info(f"📊 Rapport d'activité généré par {interaction.user} pour {jours} jours")

async def setup(bot):
    await bot.add_cog(Report(bot))