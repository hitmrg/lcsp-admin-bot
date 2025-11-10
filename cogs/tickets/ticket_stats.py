import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database, get_session

logger = logging.getLogger(__name__)


class TicketStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_stats", description="Statistiques du système de tickets"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        from models import Ticket, TicketStatus, TicketType

        with get_session() as session:
            total_tickets = session.query(Ticket).count()
            open_tickets = (
                session.query(Ticket).filter(Ticket.status == TicketStatus.OPEN).count()
            )
            closed_tickets = (
                session.query(Ticket)
                .filter(Ticket.status == TicketStatus.CLOSED)
                .count()
            )
            labo_tickets = (
                session.query(Ticket)
                .filter(Ticket.type == TicketType.JOIN_LABO)
                .count()
            )
            pole_tickets = (
                session.query(Ticket)
                .filter(Ticket.type == TicketType.JOIN_POLE)
                .count()
            )
            dev_requests = (
                session.query(Ticket).filter(Ticket.pole_requested == "DEV").count()
            )
            ia_requests = (
                session.query(Ticket).filter(Ticket.pole_requested == "IA").count()
            )
            infra_requests = (
                session.query(Ticket).filter(Ticket.pole_requested == "INFRA").count()
            )
        embed = discord.Embed(
            title="📊 Statistiques des tickets",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="📈 Vue d'ensemble",
            value=f"**Total:** {total_tickets}\n**Ouverts:** {open_tickets}\n**Fermés:** {closed_tickets}",
            inline=True,
        )
        embed.add_field(
            name="📋 Par type",
            value=f"**Laboratoire:** {labo_tickets}\n**Changement pôle:** {pole_tickets}",
            inline=True,
        )
        if pole_tickets > 0:
            embed.add_field(
                name="🏛️ Demandes par pôle",
                value=f"**DEV:** {dev_requests}\n**IA:** {ia_requests}\n**INFRA:** {infra_requests}",
                inline=True,
            )
        if total_tickets > 0:
            closed_percent = (closed_tickets / total_tickets) * 100
            bar_length = int(closed_percent / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            embed.add_field(
                name="📊 Taux de résolution",
                value=f"`{bar}` {closed_percent:.1f}%",
                inline=False,
            )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TicketStats(bot))
