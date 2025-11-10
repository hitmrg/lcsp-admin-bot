import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class TicketList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_list", description="Lister tous les tickets ouverts"
    )
    @is_admin()
    async def ticket_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        tickets = self.db.get_open_tickets()
        if not tickets:
            await interaction.followup.send(
                "📭 Aucun ticket ouvert actuellement.", ephemeral=True
            )
            return
        from views.TicketListView import TicketListView

        view = TicketListView(tickets, self.db, per_page=5)
        embed = view.get_embed(interaction)
        view.update_buttons()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TicketList(bot))
