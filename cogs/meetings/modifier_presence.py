import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class ModifyPresence(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Modifier la présence par nom de réunion
    @app_commands.command(
        name="modifier_presence", description="Modifier la présence d'un membre"
    )
    @app_commands.describe(
        reunion="Nom ou partie du nom de la réunion",
        membre="Membre Discord",
        statut="present/absent/excused",
    )
    @is_admin()
    async def modify_attendance(
        self,
        interaction: discord.Interaction,
        reunion: str,
        membre: discord.Member,
        statut: str,
    ):
        await interaction.response.defer(ephemeral=True)

        # Rechercher la réunion
        meetings = self.db.get_meeting_by_name(reunion)

        if not meetings:
            await interaction.followup.send(
                f"❌ Aucune réunion trouvée", ephemeral=True
            )
            return

        if len(meetings) > 1:
            embed = discord.Embed(
                title="⚠️ Plusieurs réunions trouvées",
                description="Précisez en utilisant l'ID: /modifier_presence_id [id]",
                color=discord.Color.orange(),
            )
            for meeting in meetings[:10]:
                embed.add_field(
                    name=f"#{meeting.id} - {meeting.title}",
                    value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}",
                    inline=False,
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        meeting = meetings[0]

        if not meeting.attendance_validated:
            await interaction.followup.send(
                "❌ L'appel n'a pas encore été validé pour cette réunion",
                ephemeral=True,
            )
            return

        member = self.db.get_member(str(membre.id))
        if not member:
            await interaction.followup.send("❌ Membre non enregistré", ephemeral=True)
            return

        valid_statuses = ["present", "absent", "excused"]
        if statut not in valid_statuses:
            await interaction.followup.send(
                f"❌ Statut invalide. Utilisez: {', '.join(valid_statuses)}",
                ephemeral=True,
            )
            return

        self.db.record_attendance(
            meeting.id, member.id, statut, modified_by=str(interaction.user.id)
        )

        await interaction.followup.send(
            f"✅ Présence modifiée: {membre.mention} → {statut}", ephemeral=True
        )

        logger.info(
            f"Présence modifiée par {interaction.user} pour la réunion {meeting.id}: {membre} → {statut}"
        )

async def setup(bot):
    await bot.add_cog(ModifyPresence(bot))