import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from models import MemberStatus
from views.memberListView import MemberListView

logger = logging.getLogger(__name__)


# cog de gestion des membres
class ListMember(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Lister les membres
    @app_commands.command(
        name="membres", description="Liste des membres du laboratoire"
    )
    @app_commands.describe(
        pole="Filtrer par pôle (DEV, IA, INFRA) (optionnel)",
        statut="Filtrer par statut (actif, inactif, suspendu) (optionnel)",
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
        
        logger.info(f"👥 Liste des membres affichée par {interaction.user} (pôle={pole}, statut={statut})")

async def setup(bot):
    await bot.add_cog(ListMember(bot))