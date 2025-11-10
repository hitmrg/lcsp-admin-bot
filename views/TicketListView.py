import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class TicketListView(discord.ui.View):
    """Vue avec pagination pour la liste des tickets"""

    def __init__(self, tickets, db, per_page=5):
        super().__init__(timeout=180)  # 3 minutes
        self.tickets = tickets
        self.db = db
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(tickets) - 1) // per_page if tickets else 0

    def get_embed(self, interaction: discord.Interaction):
        """Créer l'embed pour la page actuelle"""
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_tickets = self.tickets[start:end]

        embed = discord.Embed(
            title=f"📋 Tickets Ouverts - Page {self.current_page + 1}/{self.max_page + 1}",
            description=f"Total: {len(self.tickets)} tickets ouverts",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        if not page_tickets:
            embed.add_field(
                name="📭 Aucun ticket",
                value="Aucun ticket sur cette page",
                inline=False,
            )
            return embed

        for ticket in page_tickets:
            # Récupérer les infos du canal et utilisateur
            channel = interaction.guild.get_channel(int(ticket.channel_id))
            user = interaction.guild.get_member(int(ticket.discord_user_id))

            # Créer le titre du field
            status_emoji = {"open": "🟢", "pending": "🟡", "closed": "🔴"}.get(
                ticket.status.value, "⚪"
            )

            field_name = f"{status_emoji} Ticket #{ticket.id}"

            # Créer le contenu du field
            lines = []
            lines.append(
                f"**Utilisateur:** {user.mention if user else ticket.discord_username}"
            )
            lines.append(f"**Type:** {self._format_type(ticket.type.value)}")

            if ticket.pole_requested:
                lines.append(f"**Pôle:** {ticket.pole_requested}")

            lines.append(
                f"**Canal:** {channel.mention if channel else 'Canal supprimé'}"
            )

            if ticket.assigned_to:
                assigned = interaction.guild.get_member(int(ticket.assigned_to))
                lines.append(
                    f"**Assigné à:** {assigned.mention if assigned else 'Inconnu'}"
                )

            lines.append(f"**Créé:** <t:{int(ticket.created_at.timestamp())}:R>")

            embed.add_field(
                name=field_name,
                value="\n".join(lines),
                inline=False,
            )

        # Footer avec navigation
        embed.set_footer(
            text=f"Page {self.current_page + 1}/{self.max_page + 1} • "
            f"Tickets {start + 1}-{min(end, len(self.tickets))} sur {len(self.tickets)}"
        )

        return embed

    def _format_type(self, ticket_type):
        """Formater le type de ticket"""
        formats = {
            "join_labo": "🎫 Rejoindre le laboratoire",
            "join_pole": "🔄 Changement de pôle",
        }
        return formats.get(ticket_type, ticket_type)

    def update_buttons(self):
        """Mettre à jour l'état des boutons"""
        # Bouton précédent
        self.prev_button.disabled = self.current_page <= 0
        # Bouton suivant
        self.next_button.disabled = self.current_page >= self.max_page
        # Bouton première page
        self.first_button.disabled = self.current_page <= 0
        # Bouton dernière page
        self.last_button.disabled = self.current_page >= self.max_page

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def first_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Aller à la première page"""
        self.current_page = 0
        self.update_buttons()
        embed = self.get_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary, row=0)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Page précédente"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_embed(interaction)
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary, row=0)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Page suivante"""
        if self.current_page < self.max_page:
            self.current_page += 1
            self.update_buttons()
            embed = self.get_embed(interaction)
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def last_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Aller à la dernière page"""
        self.current_page = self.max_page
        self.update_buttons()
        embed = self.get_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="🔄 Rafraîchir", style=discord.ButtonStyle.secondary, row=1
    )
    async def refresh_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Rafraîchir la liste des tickets"""
        # Recharger les tickets depuis la base
        self.tickets = self.db.get_open_tickets()
        self.max_page = (len(self.tickets) - 1) // self.per_page if self.tickets else 0

        # Ajuster la page si nécessaire
        if self.current_page > self.max_page:
            self.current_page = self.max_page

        self.update_buttons()
        embed = self.get_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="📊 Stats", style=discord.ButtonStyle.secondary, row=1)
    async def stats_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Afficher les statistiques rapides"""
        # Compter par type et statut
        stats = {
            "total": len(self.tickets),
            "join_labo": sum(1 for t in self.tickets if t.type.value == "join_labo"),
            "join_pole": sum(1 for t in self.tickets if t.type.value == "join_pole"),
            "assigned": sum(1 for t in self.tickets if t.assigned_to),
            "unassigned": sum(1 for t in self.tickets if not t.assigned_to),
        }

        # Compter par pôle
        pole_stats = {"DEV": 0, "IA": 0, "INFRA": 0}
        for ticket in self.tickets:
            if ticket.pole_requested in pole_stats:
                pole_stats[ticket.pole_requested] += 1

        embed = discord.Embed(
            title="📊 Statistiques Rapides",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="📈 Vue d'ensemble",
            value=f"**Total ouvert:** {stats['total']}\n"
            f"**Assignés:** {stats['assigned']}\n"
            f"**Non assignés:** {stats['unassigned']}",
            inline=True,
        )

        embed.add_field(
            name="📋 Par type",
            value=f"**Laboratoire:** {stats['join_labo']}\n"
            f"**Changement pôle:** {stats['join_pole']}",
            inline=True,
        )

        if any(pole_stats.values()):
            embed.add_field(
                name="🏛️ Par pôle",
                value="\n".join(
                    f"**{pole}:** {count}"
                    for pole, count in pole_stats.items()
                    if count > 0
                ),
                inline=True,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.select(
        placeholder="Filtrer par type...",
        options=[
            discord.SelectOption(label="Tous les tickets", value="all", emoji="📋"),
            discord.SelectOption(
                label="Rejoindre le labo", value="join_labo", emoji="🎫"
            ),
            discord.SelectOption(
                label="Changement de pôle", value="join_pole", emoji="🔄"
            ),
            discord.SelectOption(label="Non assignés", value="unassigned", emoji="❓"),
            discord.SelectOption(label="Assignés", value="assigned", emoji="✅"),
        ],
        row=2,
    )
    async def filter_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        """Filtrer les tickets"""
        filter_type = select.values[0]

        # Récupérer tous les tickets
        all_tickets = self.db.get_open_tickets()

        # Appliquer le filtre
        if filter_type == "all":
            self.tickets = all_tickets
        elif filter_type == "join_labo":
            self.tickets = [t for t in all_tickets if t.type.value == "join_labo"]
        elif filter_type == "join_pole":
            self.tickets = [t for t in all_tickets if t.type.value == "join_pole"]
        elif filter_type == "unassigned":
            self.tickets = [t for t in all_tickets if not t.assigned_to]
        elif filter_type == "assigned":
            self.tickets = [t for t in all_tickets if t.assigned_to]

        # Réinitialiser la pagination
        self.current_page = 0
        self.max_page = (len(self.tickets) - 1) // self.per_page if self.tickets else 0
        self.update_buttons()

        embed = self.get_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Désactiver tous les boutons après timeout"""
        for item in self.children:
            item.disabled = True


class QuickActionModal(discord.ui.Modal, title="Action rapide sur ticket"):
    """Modal pour effectuer une action rapide sur un ticket"""

    ticket_id = discord.ui.TextInput(
        label="ID du ticket",
        placeholder="Entrez l'ID du ticket (ex: 42)",
        required=True,
        max_length=10,
    )

    action = discord.ui.TextInput(
        label="Action",
        placeholder="close, assign, info",
        required=True,
        max_length=20,
    )

    reason = discord.ui.TextInput(
        label="Raison/Note",
        style=discord.TextStyle.paragraph,
        placeholder="Raison de l'action (optionnel)",
        required=False,
        max_length=500,
    )

    def __init__(self, db):
        super().__init__()
        self.db = db

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ticket_id = int(self.ticket_id.value)
        except ValueError:
            await interaction.response.send_message(
                "❌ ID de ticket invalide", ephemeral=True
            )
            return

        # Récupérer le ticket
        tickets = self.db.get_open_tickets()
        ticket = next((t for t in tickets if t.id == ticket_id), None)

        if not ticket:
            await interaction.response.send_message(
                f"❌ Ticket #{ticket_id} introuvable", ephemeral=True
            )
            return

        action = self.action.value.lower()

        if action == "close":
            # Fermer le ticket
            self.db.close_ticket(ticket.channel_id, str(interaction.user.id))

            # Supprimer le canal si possible
            channel = interaction.guild.get_channel(int(ticket.channel_id))
            if channel:
                await channel.delete(reason=f"Fermé par {interaction.user}")

            await interaction.response.send_message(
                f"✅ Ticket #{ticket_id} fermé", ephemeral=True
            )

        elif action == "assign":
            # S'assigner le ticket
            self.db.assign_ticket(ticket.channel_id, str(interaction.user.id))
            await interaction.response.send_message(
                f"✅ Ticket #{ticket_id} vous a été assigné", ephemeral=True
            )

        elif action == "info":
            # Afficher les infos
            embed = discord.Embed(
                title=f"📊 Ticket #{ticket_id}",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Type", value=ticket.type.value, inline=True)
            embed.add_field(
                name="Utilisateur", value=f"<@{ticket.discord_user_id}>", inline=True
            )
            embed.add_field(name="Statut", value=ticket.status.value, inline=True)
            if ticket.pole_requested:
                embed.add_field(name="Pôle", value=ticket.pole_requested, inline=True)
            if ticket.reason:
                embed.add_field(name="Raison", value=ticket.reason[:1024], inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            await interaction.response.send_message(
                f"❌ Action '{action}' non reconnue. Utilisez: close, assign, info",
                ephemeral=True,
            )
