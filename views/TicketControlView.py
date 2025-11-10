import discord
import asyncio
import logging

logger = logging.getLogger(__name__)


class TicketControlView(discord.ui.View):
    """Vue avec les boutons de contrôle pour un ticket"""

    def __init__(self, db, ticket_id):
        super().__init__(timeout=None)
        self.db = db
        self.ticket_id = ticket_id

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger, row=0)
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Vérifier les permissions : admins (manage_channels) ou créateur du ticket
        if not interaction.user.guild_permissions.manage_channels:
            ticket = self.db.get_ticket_by_channel(str(interaction.channel.id))
            if ticket and ticket.discord_user_id != str(interaction.user.id):
                await interaction.response.send_message(
                    "❌ Seuls les administrateurs ou le créateur peuvent fermer ce ticket.",
                    ephemeral=True,
                )
                return

        await interaction.response.send_message(
            "⏳ Fermeture du ticket dans 5 secondes...", ephemeral=False
        )

        # Fermer le ticket en base
        ticket = self.db.close_ticket(
            str(interaction.channel.id), str(interaction.user.id)
        )

        # Log la fermeture si configuré
        try:
            settings = self.db.get_ticket_settings(str(interaction.guild.id))
            if getattr(settings, "log_channel_id", None):
                log_ch = interaction.guild.get_channel(int(settings.log_channel_id))
                if log_ch and ticket:
                    embed = discord.Embed(
                        title="🔒 Ticket Fermé",
                        description=(
                            f"Ticket #{ticket.id}\n"
                            f"Utilisateur: <@{ticket.discord_user_id}>\n"
                            f"Fermé par: {interaction.user.mention}"
                        ),
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow(),
                    )
                    await log_ch.send(embed=embed)
        except Exception:
            logger.exception("Erreur lors de l'envoi du log de fermeture de ticket")

        # Attendre puis supprimer le canal
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(
                reason=f"Ticket fermé par {interaction.user}"
            )
        except Exception:
            logger.exception("Impossible de supprimer le canal de ticket")

    @discord.ui.button(
        label="📌 Prendre en charge", style=discord.ButtonStyle.primary, row=0
    )
    async def claim_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Seuls les admins (manage_messages) peuvent prendre en charge ici
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent prendre en charge les tickets.",
                ephemeral=True,
            )
            return

        ticket = self.db.assign_ticket(
            str(interaction.channel.id), str(interaction.user.id)
        )

        if ticket:
            embed = discord.Embed(
                description=f"✅ Ticket pris en charge par {interaction.user.mention}",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Désactiver le bouton "Prendre en charge" pour éviter double-claim
            button.disabled = True
            try:
                await interaction.message.edit(view=self)
            except Exception:
                # message could be not editable (if ephemeral or deleted), ignore
                pass
        else:
            await interaction.response.send_message(
                "❌ Erreur lors de la prise en charge du ticket.", ephemeral=True
            )

    @discord.ui.button(label="📊 Info", style=discord.ButtonStyle.secondary, row=0)
    async def ticket_info(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket = self.db.get_ticket_by_channel(str(interaction.channel.id))

        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket introuvable.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📊 Informations du Ticket",
            color=discord.Color.blue(),
        )

        embed.add_field(name="ID", value=f"#{ticket.id}", inline=True)
        embed.add_field(name="Type", value=ticket.type.value, inline=True)
        embed.add_field(name="Statut", value=ticket.status.value, inline=True)
        embed.add_field(
            name="Créé le",
            value=(
                ticket.created_at.strftime("%d/%m/%Y %H:%M")
                if ticket.created_at
                else "N/A"
            ),
            inline=True,
        )

        if ticket.assigned_to:
            embed.add_field(
                name="Assigné à", value=f"<@{ticket.assigned_to}>", inline=True
            )

        if ticket.pole_requested:
            embed.add_field(
                name="Pôle demandé", value=ticket.pole_requested, inline=True
            )

        if ticket.reason:
            embed.add_field(name="Raison", value=ticket.reason[:1024], inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
