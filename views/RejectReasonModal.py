import discord
import asyncio


class RejectReasonModal(discord.ui.Modal, title="Raison du refus"):
    """Modal pour saisir la raison du refus"""

    reason = discord.ui.TextInput(
        label="Raison du refus",
        style=discord.TextStyle.paragraph,
        placeholder="Expliquez brièvement pourquoi la demande est refusée...",
        required=True,
        max_length=1000,
    )

    def __init__(self, db, pole):
        super().__init__()
        self.db = db
        self.pole = pole

    async def on_submit(self, interaction: discord.Interaction):
        ticket = self.db.get_ticket_by_channel(str(interaction.channel.id))
        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket introuvable.", ephemeral=True
            )
            return

        user = interaction.guild.get_member(int(ticket.discord_user_id))

        embed = discord.Embed(
            title="❌ Demande Refusée",
            description=f"La demande de {user.mention if user else 'l\'utilisateur'} "
            f"pour rejoindre le pôle **{self.pole}** a été refusée.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Raison", value=self.reason.value, inline=False)
        embed.add_field(name="Refusé par", value=interaction.user.mention, inline=False)

        await interaction.response.send_message(embed=embed)

        # Notifier l'utilisateur si possible
        if user:
            try:
                dm_embed = discord.Embed(
                    title=f"❌ Demande pour le pôle {self.pole} refusée",
                    description=f"Votre demande pour rejoindre le pôle **{self.pole}** "
                    f"a été refusée.",
                    color=discord.Color.red(),
                )
                dm_embed.add_field(name="Raison", value=self.reason.value, inline=False)
                dm_embed.add_field(
                    name="💡 Conseil",
                    value="Vous pouvez améliorer vos compétences et retenter plus tard, "
                    "ou postuler pour un autre pôle.",
                    inline=False,
                )
                await user.send(embed=dm_embed)
            except:
                pass  # L'utilisateur a peut-être désactivé les DMs

        # Fermer le ticket après 10 secondes
        await interaction.followup.send(
            "Ce ticket sera fermé automatiquement dans 10 secondes..."
        )
        await asyncio.sleep(10)

        self.db.close_ticket(str(interaction.channel.id), str(interaction.user.id))
        await interaction.channel.delete(
            reason=f"Demande refusée par {interaction.user}"
        )
