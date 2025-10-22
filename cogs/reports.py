# Cog Rapports (cogs/reports.py)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime, timedelta
import io
import csv
from database import Database
from models import MemberStatus


class ReportsCog(commands.Cog):
    """Génération de rapports et statistiques du LCSP"""

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(name="stats", description="Statistiques générales du LCSP")
    async def stats(self, interaction: discord.Interaction, jours: Optional[int] = 30):
        """Afficher les statistiques générales avec taux de participation global"""
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
            f"**Réunions tenues:** {global_stats['total_meetings']}\n"
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
            value += f"**Réunions:** {stats['total_meetings']}"

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

    @app_commands.command(
        name="stats_pole", description="Statistiques détaillées d'un pôle"
    )
    async def stats_pole(
        self,
        interaction: discord.Interaction,
        pole: str,  # DEV, IA, INFRA
        jours: Optional[int] = 30,
    ):
        """Statistiques détaillées pour un pôle spécifique"""
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
            f"**Réunions concernées:** {stats['total_meetings']}\n"
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

    @app_commands.command(name="rapport", description="Rapport d'activité détaillé")
    async def report(
        self,
        interaction: discord.Interaction,
        jours: Optional[int] = 30,
        format: Optional[str] = "embed",  # embed ou file
    ):
        """Générer un rapport d'activité complet"""
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
                f"**Réunions tenues:** {global_stats['total_meetings']}\n"
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

    @app_commands.command(name="export", description="Exporter toutes les données")
    async def export(
        self,
        interaction: discord.Interaction,
        type: Optional[str] = "membres",  # membres, reunions, presences, complet
    ):
        """Exporter les données en CSV"""
        await interaction.response.defer(ephemeral=True)

        output = io.StringIO()
        writer = csv.writer(output)
        filename = f"export_lcsp_{type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        if type == "membres":
            # Export des membres
            writer.writerow(
                [
                    "ID",
                    "Discord ID",
                    "Username",
                    "Nom Complet",
                    "Email",
                    "Pôle",
                    "Spécialisation",
                    "Statut",
                    "Membre Depuis",
                    "Dernière Activité",
                ]
            )

            members = self.db.get_all_members()
            for member in members:
                writer.writerow(
                    [
                        member.id,
                        member.discord_id,
                        member.username,
                        member.full_name or "",
                        member.email or "",
                        member.role or "",
                        member.specialization or "",
                        member.status.value,
                        member.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
                        member.last_active.strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )

        elif type == "reunions":
            # Export des réunions
            writer.writerow(
                [
                    "ID",
                    "Titre",
                    "Description",
                    "Date",
                    "Heure",
                    "Créateur",
                    "Organisateur ID",
                    "Pôles Ciblés",
                    "Complétée",
                    "Appel Validé",
                ]
            )

            # Récupérer toutes les réunions (pas de méthode directe, on improvise)
            with Database.get_session() as session:
                from models import Meeting

                meetings = session.query(Meeting).all()

                for meeting in meetings:
                    writer.writerow(
                        [
                            meeting.id,
                            meeting.title,
                            meeting.description or "",
                            meeting.date.strftime("%Y-%m-%d"),
                            meeting.date.strftime("%H:%M"),
                            meeting.created_by,
                            meeting.organizer_id or "",
                            meeting.target_roles or "ALL",
                            "Oui" if meeting.is_completed else "Non",
                            "Oui" if meeting.attendance_validated else "Non",
                        ]
                    )

        elif type == "presences":
            # Export des présences
            writer.writerow(
                [
                    "Réunion ID",
                    "Réunion",
                    "Membre ID",
                    "Membre",
                    "Statut",
                    "Date/Heure",
                    "Modifié Par",
                    "Date Modification",
                ]
            )

            # Récupérer toutes les présences
            with Database.get_session() as session:
                from models import Attendance, Meeting, Member

                attendances = (
                    session.query(Attendance, Meeting, Member)
                    .join(Meeting)
                    .join(Member)
                    .all()
                )

                for att, meeting, member in attendances:
                    writer.writerow(
                        [
                            meeting.id,
                            meeting.title,
                            member.id,
                            member.full_name or member.username,
                            att.status,
                            att.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            att.modified_by or "",
                            (
                                att.modified_at.strftime("%Y-%m-%d %H:%M:%S")
                                if att.modified_at
                                else ""
                            ),
                        ]
                    )

        elif type == "complet":
            # Export complet avec plusieurs feuilles simulées
            writer.writerow(["=== EXPORT COMPLET LCSP ==="])
            writer.writerow([f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
            writer.writerow([])

            # Section Membres
            writer.writerow(["=== MEMBRES ==="])
            writer.writerow(["ID", "Username", "Nom", "Email", "Pôle", "Statut"])

            members = self.db.get_all_members()
            for member in members:
                writer.writerow(
                    [
                        member.id,
                        member.username,
                        member.full_name or "",
                        member.email or "",
                        member.role or "",
                        member.status.value,
                    ]
                )

            writer.writerow([])

            # Section Statistiques
            writer.writerow(["=== STATISTIQUES (30 JOURS) ==="])
            stats = self.db.get_global_stats(days=30)
            writer.writerow(["Membres actifs", stats["active_members"]])
            writer.writerow(["Réunions tenues", stats["total_meetings"]])
            writer.writerow(
                ["Taux participation global", f"{stats['global_attendance_rate']:.1f}%"]
            )

            # Stats par pôle
            writer.writerow([])
            writer.writerow(["=== STATS PAR PÔLE ==="])
            writer.writerow(["Pôle", "Membres", "Taux Participation"])

            for pole in ["DEV", "IA", "INFRA"]:
                pole_stats = self.db.get_role_stats(pole, days=30)
                writer.writerow(
                    [
                        pole,
                        pole_stats["members_count"],
                        f"{pole_stats['avg_attendance_rate']:.1f}%",
                    ]
                )

        else:
            await interaction.followup.send(
                "❌ Type d'export invalide. Utilisez: membres, reunions, presences, ou complet",
                ephemeral=True,
            )
            return

        # Créer le fichier
        csv_data = output.getvalue()
        file = discord.File(io.BytesIO(csv_data.encode("utf-8")), filename=filename)

        await interaction.followup.send(
            f"📊 Export {type} généré avec succès", file=file, ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ReportsCog(bot))
