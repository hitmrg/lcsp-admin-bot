import discord
import asyncio
from database import Database
from views.TicketControlView import TicketControlView
from views.PoleTicketControlView import PoleTicketControlView


class TicketTypeSelect(discord.ui.Select):
    def __init__(self, db: Database):
        options = [
            discord.SelectOption(
                label="Rejoindre DEV",
                value="DEV",
                description="Postuler au pôle Développement",
            ),
            discord.SelectOption(
                label="Rejoindre IA",
                value="IA",
                description="Postuler au pôle Intelligence Artificielle",
            ),
            discord.SelectOption(
                label="Rejoindre INFRA",
                value="INFRA",
                description="Postuler au pôle Infrastructure",
            ),
            discord.SelectOption(
                label="Rejoindre le Laboratoire",
                value="LABO",
                description="Rejoindre le laboratoire LCSP",
            ),
        ]
        super().__init__(
            placeholder="Choisissez le type de ticket à ouvrir...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.db = db

    async def callback(self, interaction: discord.Interaction):
        # Réponse différée (ephemeral pour l'utilisateur)
        await interaction.response.defer(ephemeral=True)

        choice = self.values[0]

        # Récupérer / créer la catégorie de tickets
        settings = self.db.get_ticket_settings(str(interaction.guild.id))
        if not settings.tickets_enabled:
            await interaction.followup.send(
                "❌ Le système de tickets est actuellement désactivé.",
                ephemeral=True,
            )
            return

        if not settings.pole_tickets_enabled:
            await interaction.followup.send(
                "❌ Les tickets pour rejoindre un pôle sont temporairement désactivés.\n",
                ephemeral=True,
            )
            return
        category = None
        if settings and settings.ticket_category_id:
            try:
                category = interaction.guild.get_channel(
                    int(settings.ticket_category_id)
                )
            except:
                category = None

        if not category:
            category = await interaction.guild.create_category("📋 TICKETS")
            self.db.update_ticket_settings(
                str(interaction.guild.id), ticket_category_id=str(category.id)
            )

        # Préparer les permission overwrites communs
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

        # Role admin wildcard comme utilisé dans le code existant
        admin_role = discord.utils.get(interaction.guild.roles, name="*")
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                manage_channels=True,
            )

        # Si c'est un ticket pôle, ne pas ajouter le rôle dans le canal
        is_pole = choice in ("DEV", "IA", "INFRA")

        # Construire le nom du canal
        safe_name = f"ticket-{choice.lower()}-{interaction.user.name}".lower()
        channel_name = "".join(
            c if c.isalnum() or c == "-" else "-" for c in safe_name
        )[:100]

        # Créer le canal
        channel = await category.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=f"Ticket {choice} de {interaction.user.mention} | ID: {interaction.user.id}",
        )

        # Créer le ticket en base
        if is_pole:
            ticket = self.db.create_ticket(
                discord_user_id=str(interaction.user.id),
                discord_username=interaction.user.name,
                channel_id=str(channel.id),
                ticket_type="join_pole",
                pole_requested=choice,
                reason=None,
            )
        else:
            ticket = self.db.create_ticket(
                discord_user_id=str(interaction.user.id),
                discord_username=interaction.user.name,
                channel_id=str(channel.id),
                ticket_type="join_labo",
                reason=None,
            )

        # Construire l'embed d'accueil et la vue appropriée
        if is_pole:
            pole_icons = {"DEV": "💻", "IA": "🤖", "INFRA": "🛠️"}
            pole_colors = {
                "DEV": discord.Color.blue(),
                "IA": discord.Color.purple(),
                "INFRA": discord.Color.green(),
            }
            embed = discord.Embed(
                title=f"{pole_icons.get(choice,'📋')} Ticket - Rejoindre le Pôle {choice}",
                description=f"Bienvenue {interaction.user.mention} !\n\nVotre demande pour rejoindre le pôle **{choice}** va être examinée.",
                color=pole_colors.get(choice, discord.Color.blue()),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="👤 Demandeur",
                value=f"{interaction.user.mention}\n{interaction.user.name}",
                inline=True,
            )
            embed.add_field(name="🎯 Pôle demandé", value=choice, inline=True)
            embed.add_field(
                name="📅 Date",
                value=discord.utils.utcnow().strftime("%d/%m/%Y %H:%M"),
                inline=True,
            )
            embed.set_footer(text=f"Ticket ID: {ticket.id}")
            view = PoleTicketControlView(self.db, ticket.id, choice)
        else:
            embed = discord.Embed(
                title="🎫 Ticket - Rejoindre le Laboratoire LCSP",
                description=f"Bienvenue {interaction.user.mention} !\n\nUn administrateur va prendre en charge votre demande rapidement.",
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
            embed.set_footer(text=f"Ticket ID: {ticket.id}")
            view = TicketControlView(self.db, ticket.id)

        # Envoyer le message d'accueil dans le canal du ticket
        await channel.send(embed=embed, view=view)

        # Envoyer un log si configuré
        if settings and settings.log_channel_id:
            log_channel = interaction.guild.get_channel(int(settings.log_channel_id))
            if log_channel:
                log_embed = discord.Embed(
                    title=f"🆕 Nouveau Ticket {'Pôle '+choice if is_pole else 'Laboratoire'}",
                    description=f"Utilisateur: {interaction.user.mention}\nCanal: {channel.mention}",
                    color=discord.Color.blue() if is_pole else discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
                )
                await log_channel.send(embed=log_embed)

        # Confirmer à l'utilisateur
        await interaction.followup.send(
            f"✅ Votre ticket pour **{('Pôle '+choice) if is_pole else 'le laboratoire'}** a été créé : {channel.mention}",
            ephemeral=True,
        )


class TicketCreationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.db = Database()
        self.add_item(TicketTypeSelect(self.db))
