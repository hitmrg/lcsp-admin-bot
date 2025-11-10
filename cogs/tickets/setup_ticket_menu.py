import discord
from discord.ext import commands
from discord import app_commands
import logging
from views.TicketCreationView import TicketCreationView
import config

logger = logging.getLogger(__name__)


class TicketMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="setup_ticket_menu",
        description="Publier le menu de création de tickets dans un canal",
    )
    @app_commands.describe(
        channel="Canal où poster le menu (laisser vide pour utiliser la valeur par défaut)"
    )
    async def setup_ticket_menu(
        self, interaction: discord.Interaction, channel: str = None
    ):
        # Autoriser uniquement les administrateurs (ici: gérer le serveur)
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent utiliser cette commande.",
                ephemeral=True,
            )
            return

        # Trouver le canal cible
        target = None
        if channel:
            # Accept either mention, id or name
            try:
                if channel.isdigit():
                    target = interaction.guild.get_channel(int(channel))
                else:
                    # by name
                    for ch in interaction.guild.text_channels:
                        if ch.name == channel or ch.mention == channel:
                            target = ch
                            break
            except:
                target = None

        if not target:
            # Try configured CREATE_TICKET_CHANNEL name
            for ch in interaction.guild.text_channels:
                if ch.name == config.CREATE_TICKET_CHANNEL:
                    target = ch
                    break

        if not target:
            target = interaction.channel  # fallback

        # Build embed + view
        embed = discord.Embed(
            title="📩 Ouvrir un ticket",
            description="Sélectionnez le type de ticket que vous souhaitez ouvrir dans le menu ci-dessous.\n\nOptions disponibles:\n• Rejoindre un pôle (DEV / IA / INFRA)\n• Rejoindre le laboratoire LCSP",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(
            text="Sélectionnez votre option puis patientez: un canal sera créé pour votre demande."
        )

        view = TicketCreationView()

        await target.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ Menu de tickets publié dans {target.mention}", ephemeral=True
        )
        logger.info(f"Menu de tickets posté par {interaction.user} dans {target.name}")


async def setup(bot):
    await bot.add_cog(TicketMenu(bot))
