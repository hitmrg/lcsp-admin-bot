import discord
from views.adminAttendanceView import AdminAttendanceView
import logging

logger = logging.getLogger(__name__)

async def create_attendance_view(self, interaction, meeting):
        target_roles = meeting.get_target_roles()
        roles_text = "Tous" if "ALL" in target_roles else ", ".join(target_roles)

        # Récupérer les membres attendus
        expected_members = self.db.get_members_by_roles(target_roles)

        if not expected_members:
            await interaction.followup.send(
                "❌ Aucun membre correspondant aux rôles de cette réunion n'a été trouvé.",
                ephemeral=True,
            )
            return

        # Vérifier qu'il y a au moins un membre sur la première page
        first_page_members = expected_members[:5]  # 5 membres par page
        if not first_page_members:
            await interaction.followup.send(
                "❌ Erreur: Aucun membre à afficher sur la première page.",
                ephemeral=True,
            )
            return

        # Créer l'embed principal
        embed = discord.Embed(
            title=f"📢 Appel Administratif - {meeting.title}",
            description=(
                f"**Réunion ID:** {meeting.id}\n"
                f"**Pôles concernés:** {roles_text}\n"
                f"**Membres attendus:** {len(expected_members)}\n\n"
                "Utilisez l'interface ci-dessous pour gérer l'appel."
            ),
            color=discord.Color.blue(),
            timestamp=meeting.date,
        )

        embed.add_field(
            name="📅 Date de la réunion",
            value=meeting.date.strftime("%d/%m/%Y à %H:%M"),
            inline=False,
        )

        # Créer la vue Admin avec les membres de la première page
        try:
            admin_view = AdminAttendanceView(
                meeting.id, self.db, str(interaction.user.id), expected_members
            )

            # Envoyer le message avec la vue
            message = await interaction.followup.send(embed=embed, view=admin_view)
            self.active_meetings[meeting.id] = message

        except Exception as e:
            logger.error(f"Erreur lors de la création de la vue d'appel: {str(e)}")
            await interaction.followup.send(
                "❌ Une erreur est survenue lors de la création de l'interface d'appel.",
                ephemeral=True,
            )
            return