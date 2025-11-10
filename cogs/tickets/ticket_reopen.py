import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class TicketReopen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(name="ticket_reopen", description="Rouvrir un ticket fermé")
    @app_commands.describe(ticket_id="ID du ticket à rouvrir")
    @is_admin()
    async def ticket_reopen(self, interaction: discord.Interaction, ticket_id: int):
        await interaction.response.defer()
        from models import Ticket, TicketStatus

        with self.db.get_session() as session:
            ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                await interaction.followup.send(f"❌ Ticket #{ticket_id} introuvable.")
                return
            if ticket.status != TicketStatus.CLOSED:
                await interaction.followup.send(
                    f"❌ Le ticket #{ticket_id} n'est pas fermé."
                )
                return
            channel = interaction.guild.get_channel(int(ticket.channel_id))
            if channel:
                ticket.status = TicketStatus.OPEN
                ticket.closed_at = None
                ticket.closed_by = None
                session.commit()
                await interaction.followup.send(
                    f"✅ Ticket #{ticket_id} rouvert avec succès.\nCanal: {channel.mention}"
                )
            else:
                settings = self.db.get_ticket_settings(str(interaction.guild.id))
                category = None
                if settings.ticket_category_id:
                    category = interaction.guild.get_channel(
                        int(settings.ticket_category_id)
                    )
                if not category:
                    category = await interaction.guild.create_category("📋 TICKETS")
                    self.db.update_ticket_settings(
                        str(interaction.guild.id), ticket_category_id=str(category.id)
                    )
                user = interaction.guild.get_member(int(ticket.discord_user_id))
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(
                        view_channel=False
                    )
                }
                if user:
                    overwrites[user] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    )
                admin_role = discord.utils.get(interaction.guild.roles, name="*")
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, manage_messages=True
                    )
                ticket_type = "labo" if ticket.type.value == "join_labo" else "pole"
                channel_name = f"ticket-{ticket_type}-{ticket.discord_username}".lower()
                channel_name = "".join(
                    c if c.isalnum() or c == "-" else "-" for c in channel_name
                )[:100]
                new_channel = await category.create_text_channel(
                    name=channel_name,
                    overwrites=overwrites,
                    topic=f"Ticket rouvert #{ticket.id} | User: {ticket.discord_username}",
                )
                ticket.channel_id = str(new_channel.id)
                ticket.status = TicketStatus.OPEN
                ticket.closed_at = None
                ticket.closed_by = None
                session.commit()
                embed = discord.Embed(
                    title=f"🔄 Ticket #{ticket.id} Rouvert",
                    description=f"Ce ticket a été rouvert par {interaction.user.mention}",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.add_field(
                    name="Informations",
                    value=f"**Type:** {ticket.type.value}\n**Utilisateur:** <@{ticket.discord_user_id}>\n**Créé le:** {ticket.created_at.strftime('%d/%m/%Y %H:%M')}",
                    inline=False,
                )
                if ticket.reason:
                    embed.add_field(
                        name="Raison originale",
                        value=ticket.reason[:1024],
                        inline=False,
                    )
                await new_channel.send(embed=embed)
                if user:
                    await new_channel.send(
                        f"{user.mention}, votre ticket a été rouvert."
                    )
                await interaction.followup.send(
                    f"✅ Ticket #{ticket_id} rouvert avec succès.\nNouveau canal créé: {new_channel.mention}"
                )


async def setup(bot):
    await bot.add_cog(TicketReopen(bot))
