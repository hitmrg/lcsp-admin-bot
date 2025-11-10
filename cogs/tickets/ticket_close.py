import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class TicketClose(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_close", description="Fermer un ticket par son ID"
    )
    @app_commands.describe(
        ticket_id="ID du ticket à fermer", raison="Raison de la fermeture (optionnel)"
    )
    @is_admin()
    async def ticket_close(
        self,
        interaction: discord.Interaction,
        ticket_id: int,
        raison: Optional[str] = None,
    ):
        await interaction.response.defer()
        tickets = self.db.get_open_tickets()
        ticket = next((t for t in tickets if t.id == ticket_id), None)
        if not ticket:
            await interaction.followup.send(
                f"❌ Ticket #{ticket_id} introuvable ou déjà fermé."
            )
            return
        channel = interaction.guild.get_channel(int(ticket.channel_id))
        self.db.close_ticket(ticket.channel_id, str(interaction.user.id))
        if channel:
            embed = discord.Embed(
                title="🔒 Ticket fermé par un administrateur",
                description=f"Fermé par: {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow(),
            )
            if raison:
                embed.add_field(name="Raison", value=raison, inline=False)
            try:
                await channel.send(embed=embed)
                # Supprimer le canal après 5 secondes
                await discord.utils.sleep_until(
                    discord.utils.utcnow() + discord.timedelta(seconds=5)
                )
                await channel.delete(reason=f"Ticket fermé par {interaction.user}")
            except:
                pass
        await interaction.followup.send(f"✅ Ticket #{ticket_id} fermé avec succès.")
        settings = self.db.get_ticket_settings(str(interaction.guild.id))
        if settings.log_channel_id:
            log_channel = interaction.guild.get_channel(int(settings.log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title="🔒 Ticket fermé administrativement",
                    description=f"Ticket #{ticket_id}\nUtilisateur: <@{ticket.discord_user_id}>\nType: {ticket.type.value}\nFermé par: {interaction.user.mention}",
                    color=discord.Color.orange(),
                    timestamp=discord.utils.utcnow(),
                )
                if raison:
                    embed.add_field(name="Raison", value=raison, inline=False)
                await log_channel.send(embed=embed)
        logger.info(f"🔒 Ticket #{ticket_id} fermé par {interaction.user}")


async def setup(bot):
    await bot.add_cog(TicketClose(bot))
