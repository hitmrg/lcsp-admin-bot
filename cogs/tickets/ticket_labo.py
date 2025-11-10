import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from views.TicketControlView import TicketControlView

logger = logging.getLogger(__name__)


class TicketLabo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_labo",
        description="Créer un ticket pour rejoindre le laboratoire LCSP",
    )
    @app_commands.describe(
        raison="Expliquez votre motivation pour rejoindre le laboratoire (optionnel)"
    )
    async def ticket_labo(
        self, interaction: discord.Interaction, raison: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)

        # Vérifier les paramètres de tickets
        settings = self.db.get_ticket_settings(str(interaction.guild.id))
        if not settings.tickets_enabled:
            await interaction.followup.send(
                "❌ Le système de tickets est actuellement désactivé.",
                ephemeral=True,
            )
            return

        # Vérifier si l'utilisateur a déjà un ticket ouvert
        existing_ticket = self.db.get_user_open_ticket(str(interaction.user.id))
        if existing_ticket:
            channel = interaction.guild.get_channel(int(existing_ticket.channel_id))
            if channel:
                await interaction.followup.send(
                    f"❌ Vous avez déjà un ticket ouvert : {channel.mention}",
                    ephemeral=True,
                )
            else:
                # Le canal n'existe plus, fermer le ticket
                self.db.close_ticket(
                    existing_ticket.channel_id, str(interaction.user.id)
                )
                await interaction.followup.send(
                    "❌ Votre ticket précédent a été perdu. Veuillez recréer un ticket.",
                    ephemeral=True,
                )
            return

        # Créer la catégorie si elle n'existe pas
        category = None
        if settings.ticket_category_id:
            category = interaction.guild.get_channel(int(settings.ticket_category_id))

        if not category:
            # Créer une catégorie par défaut
            category = await interaction.guild.create_category("📋 TICKETS")
            self.db.update_ticket_settings(
                str(interaction.guild.id), ticket_category_id=str(category.id)
            )

        # Créer le canal du ticket
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            ),
        }

        # Ajouter les admins
        admin_role = discord.utils.get(interaction.guild.roles, name="*")
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                manage_channels=True,
            )

        # Créer le canal
        channel_name = f"ticket-labo-{interaction.user.name}".lower()
        # Nettoyer le nom (enlever caractères spéciaux)
        channel_name = "".join(
            c if c.isalnum() or c == "-" else "-" for c in channel_name
        )

        channel = await category.create_text_channel(
            name=channel_name[:100],  # Discord limite à 100 caractères
            overwrites=overwrites,
            topic=f"Ticket laboratoire de {interaction.user.mention} | ID: {interaction.user.id}",
        )

        # Créer le ticket en base de données
        ticket = self.db.create_ticket(
            discord_user_id=str(interaction.user.id),
            discord_username=interaction.user.name,
            channel_id=str(channel.id),
            ticket_type="join_labo",
            reason=raison,
        )

        # Créer l'embed d'accueil
        embed = discord.Embed(
            title="🎫 Ticket - Rejoindre le Laboratoire LCSP",
            description=f"Bienvenue {interaction.user.mention} !\n\n"
            f"Un administrateur va prendre en charge votre demande rapidement.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="👤 Demandeur",
            value=f"{interaction.user.mention}\n{interaction.user.name}",
            inline=True,
        )

        embed.add_field(
            name="📅 Date",
            value=discord.utils.utcnow().strftime("%d/%m/%Y %H:%M"),
            inline=True,
        )

        if raison:
            embed.add_field(
                name="💬 Motivation",
                value=raison[:1024],  # Discord limite à 1024 caractères
                inline=False,
            )

        embed.add_field(
            name="📝 Prochaines étapes",
            value="1. Un administrateur va vous poser quelques questions\n"
            "2. Vous serez assigné à un pôle (DEV, IA, INFRA)\n"
            "3. Votre profil sera créé dans la base de données\n"
            "4. Vous recevrez vos accès et rôles",
            inline=False,
        )

        embed.set_footer(text=f"Ticket ID: {ticket.id}")

        # Créer la vue avec les boutons
        view = TicketControlView(self.db, ticket.id)

        # Envoyer le message dans le canal
        await channel.send(embed=embed, view=view)

        # Notifier les admins si un canal de log est configuré
        if settings.log_channel_id:
            log_channel = interaction.guild.get_channel(int(settings.log_channel_id))
            if log_channel:
                log_embed = discord.Embed(
                    title="🆕 Nouveau Ticket Laboratoire",
                    description=f"Utilisateur: {interaction.user.mention}\n"
                    f"Canal: {channel.mention}",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
                )
                if raison:
                    log_embed.add_field(name="Motivation", value=raison[:1024])
                await log_channel.send(embed=log_embed)

        # Confirmer à l'utilisateur
        await interaction.followup.send(
            f"✅ Votre ticket a été créé : {channel.mention}\n"
            f"Un administrateur vous contactera bientôt.",
            ephemeral=True,
        )

        logger.info(
            f"🎫 Ticket laboratoire créé par {interaction.user} (ID: {ticket.id})"
        )


async def setup(bot):
    await bot.add_cog(TicketLabo(bot))
