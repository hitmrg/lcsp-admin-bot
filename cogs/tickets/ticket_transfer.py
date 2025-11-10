import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database, get_session
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class TicketTransfer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_transfer",
        description="Transférer un ticket à un autre administrateur",
    )
    @app_commands.describe(
        ticket_id="ID du ticket à transférer",
        admin="Administrateur à qui assigner le ticket",
    )
    @is_admin()
    async def ticket_transfer(
        self, interaction: discord.Interaction, ticket_id: int, admin: discord.Member
    ):
        await interaction.response.defer()
        if not any(role.name == "*" for role in admin.roles):
            await interaction.followup.send(
                f"❌ {admin.mention} n'est pas administrateur."
            )
            return
        from models import Ticket, TicketStatus

        with get_session() as session:
            ticket = (
                session.query(Ticket)
                .filter(Ticket.id == ticket_id, Ticket.status == TicketStatus.OPEN)
                .first()
            )
            if not ticket:
                await interaction.followup.send(
                    f"❌ Ticket #{ticket_id} introuvable ou fermé."
                )
                return
            old_assigned = ticket.assigned_to
            ticket.assigned_to = str(admin.id)
            session.commit()
        channel = interaction.guild.get_channel(int(ticket.channel_id))
        if channel:
            embed = discord.Embed(
                title="🔄 Ticket Transféré",
                description=f"Ce ticket a été transféré à {admin.mention}",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="Transféré par", value=interaction.user.mention, inline=True
            )
            if old_assigned:
                embed.add_field(
                    name="Précédemment assigné à",
                    value=f"<@{old_assigned}>",
                    inline=True,
                )
            await channel.send(embed=embed)
            await channel.send(f"{admin.mention}, ce ticket vous a été assigné.")
        await interaction.followup.send(
            f"✅ Ticket #{ticket_id} transféré à {admin.mention}"
        )


async def setup(bot):
    await bot.add_cog(TicketTransfer(bot))
