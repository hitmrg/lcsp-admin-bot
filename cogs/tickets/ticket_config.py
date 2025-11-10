import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class TicketConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_config", description="Configurer le système de tickets"
    )
    @app_commands.describe(
        activer_tickets="Activer/désactiver complètement le système de tickets",
        activer_tickets_pole="Activer/désactiver les tickets pour rejoindre un pôle",
        categorie="Catégorie où créer les tickets (optionnel)",
        log_channel="Canal pour les logs de tickets (optionnel)",
    )
    @is_admin()
    async def ticket_config(
        self,
        interaction: discord.Interaction,
        activer_tickets: Optional[bool] = None,
        activer_tickets_pole: Optional[bool] = None,
        categorie: Optional[discord.CategoryChannel] = None,
        log_channel: Optional[discord.TextChannel] = None,
    ):
        await interaction.response.defer(ephemeral=True)

        # Récupérer les paramètres actuels
        settings = self.db.get_ticket_settings(str(interaction.guild.id))

        # Préparer les mises à jour
        updates = {}
        changes = []

        if activer_tickets is not None:
            updates["tickets_enabled"] = activer_tickets
            status = "✅ Activé" if activer_tickets else "❌ Désactivé"
            changes.append(f"Système de tickets: {status}")

        if activer_tickets_pole is not None:
            updates["pole_tickets_enabled"] = activer_tickets_pole
            status = "✅ Activé" if activer_tickets_pole else "❌ Désactivé"
            changes.append(f"Tickets de pôle: {status}")

        if categorie:
            updates["ticket_category_id"] = str(categorie.id)
            changes.append(f"Catégorie: {categorie.mention}")

        if log_channel:
            updates["log_channel_id"] = str(log_channel.id)
            changes.append(f"Canal de logs: {log_channel.mention}")

        # Appliquer les mises à jour
        if updates:
            self.db.update_ticket_settings(str(interaction.guild.id), **updates)
            embed = discord.Embed(
                title="⚙️ Configuration des tickets mise à jour",
                description="\n".join(changes),
                color=discord.Color.green(),
            )
        else:
            # Afficher la configuration actuelle
            embed = discord.Embed(
                title="⚙️ Configuration actuelle des tickets",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Système de tickets",
                value="✅ Activé" if settings.tickets_enabled else "❌ Désactivé",
                inline=True,
            )

            embed.add_field(
                name="Tickets de pôle",
                value="✅ Activé" if settings.pole_tickets_enabled else "❌ Désactivé",
                inline=True,
            )

            if settings.ticket_category_id:
                category = interaction.guild.get_channel(
                    int(settings.ticket_category_id)
                )
                embed.add_field(
                    name="Catégorie",
                    value=category.mention if category else "Canal supprimé",
                    inline=True,
                )

            if settings.log_channel_id:
                log_chan = interaction.guild.get_channel(int(settings.log_channel_id))
                embed.add_field(
                    name="Canal de logs",
                    value=log_chan.mention if log_chan else "Canal supprimé",
                    inline=True,
                )

        await interaction.followup.send(embed=embed, ephemeral=True)

        logger.info(f"⚙️ Configuration tickets modifiée par {interaction.user}")


async def setup(bot):
    await bot.add_cog(TicketConfig(bot))
