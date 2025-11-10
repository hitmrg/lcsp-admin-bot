import discord
import asyncio
from views.RejectReasonModal import RejectReasonModal


class PoleTicketControlView(discord.ui.View):
    """Vue avec les boutons de contrôle pour un ticket de pôle"""

    def __init__(self, db, ticket_id, pole):
        super().__init__(timeout=None)
        self.db = db
        self.ticket_id = ticket_id
        self.pole = pole

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success, row=0)
    async def accept_request(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Vérifier les permissions
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent accepter les demandes.",
                ephemeral=True,
            )
            return

        ticket = self.db.get_ticket_by_channel(str(interaction.channel.id))
        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket introuvable.", ephemeral=True
            )
            return

        # Récupérer l'utilisateur
        user = interaction.guild.get_member(int(ticket.discord_user_id))
        if not user:
            await interaction.response.send_message(
                "❌ Utilisateur introuvable sur le serveur.", ephemeral=True
            )
            return

        # Mettre à jour le membre en base
        member = self.db.get_member(ticket.discord_user_id)
        if member:
            # Retirer l'ancien rôle si existant
            if member.role:
                old_role = discord.utils.get(interaction.guild.roles, name=member.role)
                if old_role and old_role in user.roles:
                    await user.remove_roles(old_role)

            # Mettre à jour en base
            self.db.update_member(ticket.discord_user_id, role=self.pole)

            # Ajouter le nouveau rôle Discord
            new_role = discord.utils.get(interaction.guild.roles, name=self.pole)
            if new_role:
                await user.add_roles(new_role)

            embed = discord.Embed(
                title="✅ Demande Acceptée!",
                description=f"{user.mention} a été ajouté au pôle **{self.pole}** avec succès!",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)

            # Désactiver les boutons
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

            # Fermer le ticket après 10 secondes
            await interaction.followup.send(
                "Ce ticket sera fermé automatiquement dans 10 secondes..."
            )
            await asyncio.sleep(10)

            # Fermer le ticket
            self.db.close_ticket(str(interaction.channel.id), str(interaction.user.id))
            await interaction.channel.delete(
                reason=f"Demande acceptée par {interaction.user}"
            )
        else:
            await interaction.response.send_message(
                "❌ Membre non trouvé en base de données.", ephemeral=True
            )

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger, row=0)
    async def reject_request(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Vérifier les permissions
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent refuser les demandes.",
                ephemeral=True,
            )
            return

        # Modal pour demander la raison du refus
        modal = RejectReasonModal(self.db, self.pole)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.secondary, row=0)
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Vérifier les permissions
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
        self.db.close_ticket(str(interaction.channel.id), str(interaction.user.id))

        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")

    @discord.ui.button(label="📊 Info", style=discord.ButtonStyle.secondary, row=1)
    async def ticket_info(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ticket = self.db.get_ticket_by_channel(str(interaction.channel.id))

        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket introuvable.", ephemeral=True
            )
            return

        # Récupérer les infos du membre
        member = self.db.get_member(ticket.discord_user_id)

        embed = discord.Embed(
            title="📊 Informations du Ticket", color=discord.Color.blue()
        )

        embed.add_field(name="ID", value=f"#{ticket.id}", inline=True)
        embed.add_field(name="Type", value="Changement de pôle", inline=True)
        embed.add_field(name="Statut", value=ticket.status.value, inline=True)
        embed.add_field(name="Pôle demandé", value=ticket.pole_requested, inline=True)

        if member:
            embed.add_field(
                name="Pôle actuel", value=member.role or "Aucun", inline=True
            )
            embed.add_field(
                name="Membre depuis",
                value=member.joined_at.strftime("%d/%m/%Y"),
                inline=True,
            )

        embed.add_field(
            name="Créé le",
            value=ticket.created_at.strftime("%d/%m/%Y %H:%M"),
            inline=False,
        )

        if ticket.reason:
            embed.add_field(name="Motivation", value=ticket.reason[:1024], inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
