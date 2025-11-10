import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class TicketPurge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_purge", description="Supprimer tous les canaux de tickets fermés"
    )
    @is_admin()
    async def ticket_purge(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = self.db.get_ticket_settings(str(interaction.guild.id))
        if not settings.ticket_category_id:
            await interaction.followup.send(
                "❌ Aucune catégorie de tickets configurée.", ephemeral=True
            )
            return
        category = interaction.guild.get_channel(int(settings.ticket_category_id))
        if not category:
            await interaction.followup.send(
                "❌ Catégorie de tickets introuvable.", ephemeral=True
            )
            return
        from models import Ticket, TicketStatus

        with Database.get_session() as session:
            closed_tickets = (
                session.query(Ticket).filter(Ticket.status == TicketStatus.CLOSED).all()
            )
        deleted_count = 0
        for ticket in closed_tickets:
            channel = interaction.guild.get_channel(int(ticket.channel_id))
            if channel and channel.category == category:
                try:
                    await channel.delete(reason=f"Purge par {interaction.user}")
                    deleted_count += 1
                except:
                    pass
        embed = discord.Embed(
            title="🗑️ Purge des tickets",
            description=f"**{deleted_count}** canaux de tickets fermés ont été supprimés.",
            color=(
                discord.Color.green() if deleted_count > 0 else discord.Color.orange()
            ),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"🗑️ Purge de {deleted_count} tickets par {interaction.user}")


async def setup(bot):
    await bot.add_cog(TicketPurge(bot))
