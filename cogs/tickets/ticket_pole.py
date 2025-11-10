import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from views.PoleTicketControlView import PoleTicketControlView

logger = logging.getLogger(__name__)


class TicketPole(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(
        name="ticket_pole",
        description="Créer un ticket pour rejoindre un pôle spécifique",
    )
    @app_commands.describe(
        pole="Le pôle que vous souhaitez rejoindre (DEV, IA, INFRA)",
        raison="Expliquez votre expérience et motivation pour ce pôle (optionnel)",
    )
    @app_commands.choices(
        pole=[
            app_commands.Choice(name="🖥️ DEV - Développement", value="DEV"),
            app_commands.Choice(name="🤖 IA - Intelligence Artificielle", value="IA"),
            app_commands.Choice(name="🛠️ INFRA - Infrastructure", value="INFRA"),
        ]
    )
    async def ticket_pole(
        self,
        interaction: discord.Interaction,
        pole: str,
        raison: Optional[str] = None,
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

        if not settings.pole_tickets_enabled:
            await interaction.followup.send(
                "❌ Les tickets pour rejoindre un pôle sont temporairement désactivés.\n"
                "Utilisez `/ticket_labo` pour rejoindre le laboratoire d'abord.",
                ephemeral=True,
            )
            return

        # Vérifier si l'utilisateur est déjà membre
        member = self.db.get_member(str(interaction.user.id))
        if not member:
            await interaction.followup.send(
                "❌ Vous devez d'abord être membre du laboratoire.\n"
                "Utilisez `/ticket_labo` pour rejoindre le laboratoire.",
                ephemeral=True,
            )
            return

        # Vérifier si l'utilisateur a déjà ce rôle
        if member.role == pole:
            await interaction.followup.send(
                f"❌ Vous êtes déjà membre du pôle {pole}.",
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

        # Ajouter les admins et les responsables du pôle
        admin_role = discord.utils.get(interaction.guild.roles, name="*")
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                manage_channels=True,
            )

        # Ajouter les membres du pôle concerné (pour qu'ils puissent aider)
        pole_role = discord.utils.get(interaction.guild.roles, name=pole)
        if pole_role:
            overwrites[pole_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True
            )

        # Créer le canal
        pole_icons = {"DEV": "💻", "IA": "🤖", "INFRA": "🛠️"}
        channel_name = f"ticket-{pole.lower()}-{interaction.user.name}".lower()
        # Nettoyer le nom
        channel_name = "".join(
            c if c.isalnum() or c == "-" else "-" for c in channel_name
        )

        channel = await category.create_text_channel(
            name=channel_name[:100],
            overwrites=overwrites,
            topic=f"Ticket pôle {pole} de {interaction.user.mention} | ID: {interaction.user.id}",
        )

        # Créer le ticket en base de données
        ticket = self.db.create_ticket(
            discord_user_id=str(interaction.user.id),
            discord_username=interaction.user.name,
            channel_id=str(channel.id),
            ticket_type="join_pole",
            pole_requested=pole,
            reason=raison,
        )

        # Créer l'embed d'accueil
        pole_icon = pole_icons.get(pole, "📋")
        pole_colors = {
            "DEV": discord.Color.blue(),
            "IA": discord.Color.purple(),
            "INFRA": discord.Color.green(),
        }

        embed = discord.Embed(
            title=f"{pole_icon} Ticket - Rejoindre le Pôle {pole}",
            description=f"Bienvenue {interaction.user.mention} !\n\n"
            f"Votre demande pour rejoindre le pôle **{pole}** va être examinée.",
            color=pole_colors.get(pole, discord.Color.blue()),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="👤 Demandeur",
            value=f"{interaction.user.mention}\n{interaction.user.name}",
            inline=True,
        )

        embed.add_field(name="🎯 Pôle demandé", value=pole, inline=True)

        embed.add_field(
            name="📅 Date",
            value=discord.utils.utcnow().strftime("%d/%m/%Y %H:%M"),
            inline=True,
        )

        # Afficher le pôle actuel s'il en a un
        if member.role:
            embed.add_field(
                name="📍 Pôle actuel",
                value=member.role,
                inline=True,
            )

        if raison:
            embed.add_field(
                name="💬 Motivation & Expérience",
                value=raison[:1024],
                inline=False,
            )

        # Informations sur le pôle
        pole_info = {
            "DEV": "**Compétences attendues:**\n"
            "• Langages de programmation (Python, Java, JS...)\n"
            "• Développement web/mobile\n"
            "• Bases de données\n"
            "• Git et outils de développement",
            "IA": "**Compétences attendues:**\n"
            "• Machine Learning / Deep Learning\n"
            "• Python et frameworks (TensorFlow, PyTorch...)\n"
            "• Mathématiques et statistiques\n"
            "• Traitement de données",
            "INFRA": "**Compétences attendues:**\n"
            "• Administration système (Linux/Windows)\n"
            "• Réseaux et protocoles\n"
            "• Cloud et virtualisation\n"
            "• Sécurité et hardening",
        }

        embed.add_field(
            name=f"📚 À propos du pôle {pole}",
            value=pole_info.get(pole, "Pôle technique du laboratoire"),
            inline=False,
        )

        embed.add_field(
            name="📝 Prochaines étapes",
            value="1. Un responsable du pôle va évaluer votre demande\n"
            "2. Vous pourrez être invité à présenter vos projets/compétences\n"
            "3. Si accepté, vous recevrez le rôle du pôle\n"
            "4. Vous serez intégré aux projets et réunions du pôle",
            inline=False,
        )

        embed.set_footer(text=f"Ticket ID: {ticket.id}")

        # Créer la vue avec les boutons
        view = PoleTicketControlView(self.db, ticket.id, pole)

        # Envoyer le message dans le canal
        message = await channel.send(embed=embed, view=view)

        # Mentionner le rôle du pôle pour notifier les membres
        if pole_role:
            await channel.send(
                f"{pole_role.mention} - Nouvelle demande pour rejoindre le pôle!"
            )

        # Notifier les admins si un canal de log est configuré
        if settings.log_channel_id:
            log_channel = interaction.guild.get_channel(int(settings.log_channel_id))
            if log_channel:
                log_embed = discord.Embed(
                    title=f"🆕 Nouveau Ticket Pôle {pole}",
                    description=f"Utilisateur: {interaction.user.mention}\n"
                    f"Canal: {channel.mention}\n"
                    f"Pôle actuel: {member.role or 'Aucun'}\n"
                    f"Pôle demandé: {pole}",
                    color=pole_colors.get(pole, discord.Color.blue()),
                    timestamp=discord.utils.utcnow(),
                )
                if raison:
                    log_embed.add_field(name="Motivation", value=raison[:1024])
                await log_channel.send(embed=log_embed)

        # Confirmer à l'utilisateur
        await interaction.followup.send(
            f"✅ Votre ticket pour rejoindre le pôle **{pole}** a été créé : {channel.mention}\n"
            f"Les membres du pôle ont été notifiés.",
            ephemeral=True,
        )

        logger.info(
            f"🎫 Ticket pôle {pole} créé par {interaction.user} (ID: {ticket.id})"
        )


async def setup(bot):
    await bot.add_cog(TicketPole(bot))
