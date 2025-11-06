import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin
from views.createAttendance import create_attendance_view

logger = logging.getLogger(__name__)


# cog de gestion des réunions
class Appel(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Lancer l'appel pour une réunion par nom
    @app_commands.command(
        name="appel", description="Faire l'appel pour une réunion (nom partiel)"
    )
    @app_commands.describe(reunion="Nom ou partie du nom de la réunion")
    @is_admin()
    async def start_attendance(self, interaction: discord.Interaction, reunion: str):
        await interaction.response.defer()

        # Rechercher la réunion par nom
        meetings = self.db.get_meeting_by_name(reunion)

        if not meetings:
            await interaction.followup.send(
                f"❌ Aucune réunion trouvée avec le nom '{reunion}'"
            )
            return

        if len(meetings) > 1:
            # Plusieurs réunions trouvées, demander de préciser
            embed = discord.Embed(
                title="⚠️ Plusieurs réunions trouvées",
                description="Veuillez préciser en utilisant l'ID:",
                color=discord.Color.orange(),
            )
            for meeting in meetings[:5]:  # Limiter à 5
                embed.add_field(
                    name=f"#{meeting.id} - {meeting.title}",
                    value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}\n"
                    f"Organisateur: <@{meeting.created_by}>",
                    inline=False,
                )
            embed.set_footer(text="Utilisez: /appel_id [id]")
            await interaction.followup.send(embed=embed)
            return

        meeting = meetings[0]

        # Empêcher de relancer l'appel si déjà validé
        if meeting.attendance_validated:
            await interaction.followup.send(
                "❌ L'appel pour cette réunion a déjà été validé et ne peut pas être relancé"
            )
            return

        # Créer la vue Admin pour gérer l'appel
        await create_attendance_view(interaction, meeting)

        logger.info(
            f"📝 Appel lancé pour la réunion '{meeting.title}' (ID: {meeting.id}) par {interaction.user} (ID: {interaction.user.id})"
        )

async def setup(bot):
    await bot.add_cog(Appel(bot))