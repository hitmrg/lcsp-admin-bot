import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime
import logging
import io
import csv
from database import Database

logger = logging.getLogger(__name__)


class Export(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Exporter les données en CSV
    @app_commands.command(name="export", description="Exporter toutes les données")
    @app_commands.describe(
        type="Type de données à exporter (membres, reunions, presences, complet)"
    )
    async def export(
        self,
        interaction: discord.Interaction,
        type: Optional[str] = "membres",  # membres, reunions, presences, complet
    ):
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
            writer.writerow(["Réunions complétées", stats["total_meetings"]])
            writer.writerow(["Réunions à venir", stats.get("upcoming_meetings", 0)])
            writer.writerow(
                ["Taux participation global", f"{stats['global_attendance_rate']:.1f}%"]
            )

            # Stats par pôle
            writer.writerow([])
            writer.writerow(["=== STATS PAR PÔLE ==="])
            writer.writerow(["Pôle", "Membres", "Taux Participation", "Réunions à venir"])

            for pole in ["DEV", "IA", "INFRA"]:
                pole_stats = self.db.get_role_stats(pole, days=30)
                writer.writerow(
                    [
                        pole,
                        pole_stats["members_count"],
                        f"{pole_stats['avg_attendance_rate']:.1f}%",
                        pole_stats.get("upcoming_meetings", 0),
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

        logger.info(f"📊 Export {type} généré par {interaction.user}")

async def setup(bot):
    await bot.add_cog(Export(bot))