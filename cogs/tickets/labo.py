# Fichier cogs/tickets/labo.py (commande création ticket pour rejoindre laboratoire)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from config import BASIC_ROLES
from database import Database

logger = logging.getLogger("LCSP_BOT_ADMIN")

class LaboTicket(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Commande slash pour créer un ticket de laboratoire dans une catégorie spécifique (vérifie que la catégorie Tickets existe)
    @app_commands.command(
        name="labo_ticket",
        description="Créer un ticket pour rejoindre le laboratoire.",
    )
    @app_commands.describe()
    async def labo_ticket(self, interaction: discord.Interaction):
        logger.info(f"Commande /labo_ticket utilisée par {interaction.user}")

        # Vérifier si l'utilisateur a déjà un ticket ouvert
        existing_ticket = await self.db.get_labo_ticket(interaction.user.id)
        if existing_ticket:
            await interaction.response.send_message(
                "Vous avez déjà un ticket de laboratoire ouvert.", ephemeral=True
            )
            return

        # Créer un nouveau canal privé pour le ticket
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        for role_name in BASIC_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            # Sanitize username for channel name
            name=f"labo-ticket-{''.join(c if c.isalnum() or c == '-' else '-' for c in interaction.user.name.lower().replace(' ', '-'))}",
            overwrites=overwrites,
            topic=f"Ticket de laboratoire pour {interaction.user.mention}",
        )

        # Enregistrer le ticket dans la base de données
        try:
            await self.db.create_labo_ticket(interaction.user.id, channel.id, reason)
        except Exception as e:
            logger.error(f"Erreur lors de la création du ticket en base de données: {e}")
            await channel.delete(reason="Erreur lors de la création du ticket en base de données")
            await interaction.response.send_message(
                "Une erreur est survenue lors de la création du ticket. Veuillez réessayer plus tard.", ephemeral=True
            )
            return

        # Envoyer un message de bienvenue dans le canal du ticket
        await channel.send(
            f"Bonjour {interaction.user.mention}, bienvenue dans votre ticket de laboratoire! "
            "Un membre de l'adminisration vous assistera bientôt."
        )

        # Répondre à l'utilisateur
        await interaction.response.send_message(
            f"Votre ticket de laboratoire a été créé: {channel.mention}", ephemeral=True
        )


# Fonction de setup du cog
async def setup(bot):
    await bot.add_cog(LaboTicket(bot))