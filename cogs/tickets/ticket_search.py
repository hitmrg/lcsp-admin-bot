import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database, get_session
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class TicketSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_search", description="Rechercher des tickets par utilisateur ou ID"
    )
    @app_commands.describe(
        utilisateur="Rechercher les tickets d'un utilisateur spécifique",
        ticket_id="Rechercher un ticket par son ID",
        inclure_fermes="Inclure les tickets fermés dans la recherche",
    )
    @is_admin()
    async def ticket_search(
        self,
        interaction: discord.Interaction,
        utilisateur: Optional[discord.User] = None,
        ticket_id: Optional[int] = None,
        inclure_fermes: Optional[bool] = False,
    ):
        await interaction.response.defer(ephemeral=True)
        from models import Ticket, TicketStatus

        with get_session() as session:
            query = session.query(Ticket)
            if utilisateur:
                query = query.filter(Ticket.discord_user_id == str(utilisateur.id))
            if ticket_id:
                query = query.filter(Ticket.id == ticket_id)
            if not inclure_fermes:
                query = query.filter(Ticket.status != TicketStatus.CLOSED)
            tickets = query.order_by(Ticket.created_at.desc()).all()
        if not tickets:
            await interaction.followup.send(
                "❌ Aucun ticket trouvé avec ces critères.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title=f"🔍 Résultats de recherche ({len(tickets)} tickets)",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        for ticket in tickets[:10]:
            channel = interaction.guild.get_channel(int(ticket.channel_id))
            status_emoji = {"open": "🟢", "closed": "🔴", "pending": "🟡"}.get(
                ticket.status.value, "⚪"
            )
            field_name = f"{status_emoji} Ticket #{ticket.id}"
            field_value = f"**Utilisateur:** <@{ticket.discord_user_id}>\n**Type:** {ticket.type.value}\n"
            if ticket.pole_requested:
                field_value += f"**Pôle:** {ticket.pole_requested}\n"
            if channel:
                field_value += f"**Canal:** {channel.mention}\n"
            elif ticket.status.value == "open":
                field_value += f"**Canal:** ⚠️ Supprimé\n"
            field_value += f"**Créé:** {ticket.created_at.strftime('%d/%m/%Y %H:%M')}\n"
            if ticket.status.value == "closed" and ticket.closed_at:
                field_value += (
                    f"**Fermé:** {ticket.closed_at.strftime('%d/%m/%Y %H:%M')}\n"
                )
                if ticket.closed_by:
                    field_value += f"**Par:** <@{ticket.closed_by}>\n"
            embed.add_field(name=field_name, value=field_value, inline=False)
        if len(tickets) > 10:
            embed.set_footer(text=f"... et {len(tickets) - 10} autres résultats")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TicketSearch(bot))
