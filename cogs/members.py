# Cog Membres (cogs/members.py)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from config import ADMIN_ROLES
from database import Database
from models import MemberStatus

logger = logging.getLogger(__name__)


def is_admin():
    async def predicate(interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False
        return any(role.name in ADMIN_ROLES for role in member.roles)

    return app_commands.check(predicate)


# cog de gestion des membres
class MembersCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(name="membre_add", description="Ajouter un membre")
    @is_admin()
    async def add_member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nom: str,
        pole: str,  # DEV, IA, INFRA
        email: Optional[str] = None,
        specialisation: Optional[str] = None,
    ):
        """Ajouter un nouveau membre (email optionnel)"""
        await interaction.response.defer()

        # Vérifier si le membre existe
        if self.db.get_member(str(user.id)):
            await interaction.followup.send(f"❌ {user.mention} est déjà enregistré")
            return

        # Vérifier le pôle
        valid_poles = ["DEV", "IA", "INFRA"]
        pole = pole.upper()
        if pole not in valid_poles:
            await interaction.followup.send(
                f"❌ Pôle invalide: {pole}\nPôles valides: {', '.join(valid_poles)}"
            )
            return

        # Ajouter le membre
        member = self.db.add_member(
            discord_id=str(user.id),
            username=user.name,
            full_name=nom,
            email=email,
            role=pole,
            specialization=specialisation,
        )

        # Ajouter le rôle Discord correspondant
        discord_role = discord.utils.get(interaction.guild.roles, name=pole)
        if discord_role:
            try:
                await user.add_roles(discord_role)
            except:
                pass

        # Créer l'embed de confirmation
        embed = discord.Embed(
            title="✅ Nouveau membre LCSP", color=discord.Color.green()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Discord", value=user.mention, inline=True)
        embed.add_field(name="Nom", value=nom, inline=True)
        embed.add_field(name="Pôle", value=pole, inline=True)
        if email:
            embed.add_field(name="Email", value=email, inline=True)
        if specialisation:
            embed.add_field(name="Spécialisation", value=specialisation, inline=True)

        embed.set_footer(text=f"ID: {member.id}")

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="membre_info", description="Informations détaillées d'un membre"
    )
    async def member_info(
        self, interaction: discord.Interaction, user: Optional[discord.Member] = None
    ):
        """Voir les informations détaillées d'un membre"""
        await interaction.response.defer()

        target = user or interaction.user
        member = self.db.get_member(str(target.id))

        if not member:
            await interaction.followup.send(f"❌ {target.mention} n'est pas enregistré")
            return

        # Calculer les stats
        stats = self.db.get_member_stats(member.id)

        # Créer l'embed
        embed = discord.Embed(title=f"👤 Fiche membre LCSP", color=discord.Color.blue())
        embed.set_thumbnail(url=target.display_avatar.url)

        # Informations principales
        embed.add_field(
            name="📋 Identité",
            value=f"**Nom:** {member.full_name or 'Non renseigné'}\n"
            f"**Discord:** {target.mention}\n"
            f"**Username:** {member.username}",
            inline=False,
        )

        embed.add_field(
            name="💼 Professionnel",
            value=f"**Pôle:** {member.role or 'Non défini'}\n"
            f"**Spécialisation:** {member.specialization or 'Non renseignée'}\n"
            f"**Email:** {member.email or 'Non renseigné'}",
            inline=False,
        )

        embed.add_field(
            name="📊 Statistiques",
            value=f"**Statut:** {member.status.value}\n"
            f"**Membre depuis:** {member.joined_at.strftime('%d/%m/%Y')}\n"
            f"**Dernière activité:** {member.last_active.strftime('%d/%m/%Y')}\n"
            f"**Présence (30j):** {stats['rate']:.1f}% ({stats['attended']}/{stats['total']} réunions)",
            inline=False,
        )

        embed.set_footer(text=f"ID Membre: {member.id}")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="membre_update", description="Modifier un membre")
    @is_admin()
    async def update_member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nom: Optional[str] = None,
        email: Optional[str] = None,
        pole: Optional[str] = None,
        specialisation: Optional[str] = None,
        statut: Optional[str] = None,  # actif, inactif, suspendu
    ):
        """Modifier les informations d'un membre"""
        await interaction.response.defer(ephemeral=True)

        updates = {}
        if nom:
            updates["full_name"] = nom
        if email:
            updates["email"] = email
        if pole:
            pole = pole.upper()
            if pole not in ["DEV", "IA", "INFRA"]:
                await interaction.followup.send(
                    "❌ Pôle invalide. Utilisez: DEV, IA, INFRA", ephemeral=True
                )
                return
            updates["role"] = pole
        if specialisation:
            updates["specialization"] = specialisation
        if statut:
            statut_map = {
                "actif": MemberStatus.ACTIVE,
                "inactif": MemberStatus.INACTIVE,
                "suspendu": MemberStatus.SUSPENDED,
            }
            if statut.lower() not in statut_map:
                await interaction.followup.send(
                    "❌ Statut invalide. Utilisez: actif, inactif, suspendu",
                    ephemeral=True,
                )
                return
            updates["status"] = statut_map[statut.lower()]

        if not updates:
            await interaction.followup.send(
                "❌ Aucune modification spécifiée", ephemeral=True
            )
            return

        member = self.db.update_member(str(user.id), **updates)

        if member:
            # Mettre à jour le rôle Discord si nécessaire
            if pole:
                # Retirer les anciens rôles de pôle
                for role_name in ["DEV", "IA", "INFRA"]:
                    old_role = discord.utils.get(
                        interaction.guild.roles, name=role_name
                    )
                    if old_role and old_role in user.roles:
                        await user.remove_roles(old_role)

                # Ajouter le nouveau rôle
                new_role = discord.utils.get(interaction.guild.roles, name=pole)
                if new_role:
                    await user.add_roles(new_role)

            await interaction.followup.send(
                f"✅ {user.mention} mis à jour avec succès", ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ Membre non trouvé", ephemeral=True)

    @app_commands.command(name="membre_delete", description="Supprimer un membre")
    @is_admin()
    async def delete_member(
        self, interaction: discord.Interaction, user: discord.Member
    ):
        """Supprimer un membre de la base de données"""
        await interaction.response.defer(ephemeral=True)

        if self.db.delete_member(str(user.id)):
            # Retirer les rôles de pôle
            for role_name in ["DEV", "IA", "INFRA"]:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role and role in user.roles:
                    await user.remove_roles(role)

            await interaction.followup.send(
                f"✅ {user.mention} supprimé de la base de données", ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ Membre non trouvé", ephemeral=True)

    @app_commands.command(
        name="membres", description="Liste des membres du laboratoire"
    )
    async def list_members(
        self,
        interaction: discord.Interaction,
        pole: Optional[str] = None,
        statut: Optional[str] = None,
    ):
        """Afficher la liste des membres sous forme de tableau"""
        await interaction.response.defer()

        # Parser les filtres
        status_filter = None
        if statut:
            statut_map = {
                "actif": MemberStatus.ACTIVE,
                "inactif": MemberStatus.INACTIVE,
                "suspendu": MemberStatus.SUSPENDED,
            }
            status_filter = statut_map.get(statut.lower())

        role_filter = pole.upper() if pole else None

        # Récupérer les membres
        members = self.db.get_all_members(status=status_filter, role=role_filter)

        if not members:
            msg = "Aucun membre trouvé"
            if pole:
                msg += f" dans le pôle {pole.upper()}"
            if statut:
                msg += f" avec le statut {statut}"
            await interaction.followup.send(msg)
            return

        # Créer plusieurs embeds si nécessaire (max 10 membres par embed pour la lisibilité)
        embeds = []
        members_per_page = 10

        for i in range(0, len(members), members_per_page):
            page_members = members[i : i + members_per_page]

            # Titre de l'embed
            title = f"👥 Membres LCSP"
            if pole:
                title += f" - Pôle {pole.upper()}"
            if statut:
                title += f" - {statut.capitalize()}"

            embed = discord.Embed(
                title=title,
                description=f"Page {i//members_per_page + 1}/{(len(members)-1)//members_per_page + 1}",
                color=discord.Color.blue(),
            )

            # Créer le tableau
            # En-tête du tableau
            table = "```\n"
            table += f"{'Nom':<20} {'Pôle':<8} {'Statut':<10} {'Présence':<10}\n"
            table += "-" * 50 + "\n"

            for member in page_members:
                # Récupérer les stats de présence
                stats = self.db.get_member_stats(member.id, days=30)

                # Tronquer le nom si trop long
                name = (member.full_name or member.username)[:19]
                pole_str = (member.role or "N/A")[:7]
                status_str = member.status.value[:9]
                presence = f"{stats['rate']:.0f}%"

                table += f"{name:<20} {pole_str:<8} {status_str:<10} {presence:<10}\n"

            table += "```"

            embed.add_field(name="📊 Tableau des membres", value=table, inline=False)

            # Statistiques en bas
            if i == 0:  # Seulement sur la première page
                # Compter par pôle
                poles_count = {}
                for m in members:
                    if m.role:
                        poles_count[m.role] = poles_count.get(m.role, 0) + 1

                stats_text = f"**Total:** {len(members)} membres\n"
                for pole_name, count in poles_count.items():
                    stats_text += f"**{pole_name}:** {count}\n"

                embed.add_field(name="📈 Répartition", value=stats_text, inline=True)

                # Compter par statut
                status_count = {}
                for m in members:
                    status_count[m.status.value] = (
                        status_count.get(m.status.value, 0) + 1
                    )

                status_text = ""
                for status_name, count in status_count.items():
                    status_text += f"**{status_name.capitalize()}:** {count}\n"

                embed.add_field(name="📋 Statuts", value=status_text, inline=True)

            embed.set_footer(text=f"Laboratoire de Cybersécurité SUPINFO Paris")
            embeds.append(embed)

        # Si une seule page, envoyer directement
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0])
        else:
            # Créer une vue avec pagination
            view = MemberListView(embeds)
            await interaction.followup.send(embed=embeds[0], view=view)

    @app_commands.command(name="membre_search", description="Rechercher un membre")
    async def search_member(self, interaction: discord.Interaction, recherche: str):
        """Rechercher un membre par nom ou username"""
        await interaction.response.defer()

        members = self.db.get_all_members()

        # Filtrer les membres
        results = []
        search_lower = recherche.lower()
        for member in members:
            if (
                search_lower in (member.full_name or "").lower()
                or search_lower in member.username.lower()
                or search_lower in (member.email or "").lower()
            ):
                results.append(member)

        if not results:
            await interaction.followup.send(
                f"❌ Aucun membre trouvé pour '{recherche}'"
            )
            return

        # Créer l'embed des résultats
        embed = discord.Embed(
            title=f"🔍 Résultats de recherche",
            description=f"Recherche: **{recherche}**\n{len(results)} résultat(s)",
            color=discord.Color.blue(),
        )

        for member in results[:10]:  # Limiter à 10 résultats
            # Récupérer l'utilisateur Discord
            discord_user = interaction.guild.get_member(int(member.discord_id))
            user_mention = (
                f"<@{member.discord_id}>" if discord_user else "Utilisateur introuvable"
            )

            embed.add_field(
                name=member.full_name or member.username,
                value=f"Discord: {user_mention}\n"
                f"Pôle: {member.role or 'Non défini'}\n"
                f"Statut: {member.status.value}",
                inline=True,
            )

        if len(results) > 10:
            embed.set_footer(text=f"... et {len(results) - 10} autres résultats")

        await interaction.followup.send(embed=embed)


class MemberListView(discord.ui.View):
    """Vue pour la pagination de la liste des membres"""

    def __init__(self, embeds):
        super().__init__(timeout=180)  # 3 minutes
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        """Mettre à jour l'état des boutons"""
        self.previous.disabled = self.current_page == 0
        self.next.disabled = self.current_page >= len(self.embeds) - 1

    @discord.ui.button(
        label="◀ Précédent", style=discord.ButtonStyle.primary, disabled=True
    )
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Page précédente"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(
                embed=self.embeds[self.current_page], view=self
            )

    @discord.ui.button(label="Suivant ▶", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page suivante"""
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(
                embed=self.embeds[self.current_page], view=self
            )

    @discord.ui.button(label="🏠", style=discord.ButtonStyle.secondary)
    async def home(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retour à la première page"""
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[0], view=self)


async def setup(bot):
    await bot.add_cog(MembersCog(bot))
