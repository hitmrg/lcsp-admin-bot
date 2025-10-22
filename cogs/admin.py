# Cog Admin (cogs/admin.py)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from config import ADMIN_ROLES
from database import Database

logger = logging.getLogger(__name__)


def is_admin():
    """Vérificateur de permissions admin"""

    async def predicate(interaction: discord.Interaction):
        member = interaction.user

        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id)

        if not member:
            logger.warning(f"[ADMIN CHECK] Aucun membre trouvé pour {interaction.user}")
            return False

        role_names = [r.name for r in member.roles]
        logger.info(f"[ADMIN CHECK] Utilisateur: {member} | Rôles: {role_names}")

        is_admin = any(role.name in ADMIN_ROLES for role in member.roles)
        if not is_admin:
            logger.warning(
                f"[ADMIN CHECK] {member} n'a pas un rôle admin. ADMIN_ROLES={ADMIN_ROLES}"
            )

        return is_admin

    return app_commands.check(predicate)


# Cog d'administration
class AdminCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @app_commands.command(name="setup", description="Initialiser le serveur LCSP")
    @is_admin()
    async def setup(self, interaction: discord.Interaction):
        """Initialiser la structure du serveur"""
        await interaction.response.defer()

        guild = interaction.guild
        created = []
        errors = []

        # Créer les rôles s'ils n'existent pas
        roles_to_create = {
            "DEV": discord.Color.blue(),
            "IA": discord.Color.purple(),
            "INFRA": discord.Color.green(),
            "*": discord.Color.red(),
        }

        for role_name, color in roles_to_create.items():
            if not discord.utils.get(guild.roles, name=role_name):
                try:
                    await guild.create_role(name=role_name, color=color)
                    created.append(f"Rôle: {role_name}")
                except Exception as e:
                    errors.append(f"Rôle {role_name}: {str(e)}")

        # Structure des catégories et canaux
        categories = {
            "👑 ADMINISTRATION": ["╭🔑・logs", "╭📑・documents", "╭📢・annonces"],
            "🏛️ LABORATOIRE LCSP": ["╭💬・général", "╭📅・planning", "╭📊・rapports"],
            "💻 PÔLES TECHNIQUES": ["╭🛠️・infra", "╭💾・dev", "╭🤖・ia"],
        }

        # Créer les catégories et canaux
        for category_name, channels in categories.items():
            # Vérifier si la catégorie existe
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                try:
                    category = await guild.create_category(category_name)
                    created.append(f"Catégorie: {category_name}")
                except Exception as e:
                    errors.append(f"Catégorie {category_name}: {str(e)}")
                    continue

            # Créer les canaux
            for channel_name in channels:
                if not discord.utils.get(category.channels, name=channel_name):
                    try:
                        await guild.create_text_channel(channel_name, category=category)
                        created.append(f"Canal: {channel_name}")
                    except Exception as e:
                        errors.append(f"Canal {channel_name}: {str(e)}")

        # Créer l'embed de résultat
        if created or errors:
            embed = discord.Embed(
                title="⚙️ Configuration du serveur LCSP",
                color=discord.Color.green() if not errors else discord.Color.orange(),
            )

            if created:
                embed.add_field(
                    name="✅ Éléments créés",
                    value="\n".join(f"• {item}" for item in created[:10]),
                    inline=False,
                )
                if len(created) > 10:
                    embed.add_field(
                        name="",
                        value=f"... et {len(created) - 10} autres éléments",
                        inline=False,
                    )

            if errors:
                embed.add_field(
                    name="❌ Erreurs rencontrées",
                    value="\n".join(f"• {error}" for error in errors[:5]),
                    inline=False,
                )
        else:
            embed = discord.Embed(
                title="ℹ️ Configuration",
                description="Tous les éléments sont déjà configurés",
                color=discord.Color.blue(),
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="announce", description="Faire une annonce structurée")
    @is_admin()
    async def announce(
        self,
        interaction: discord.Interaction,
        titre: str,
        section1: Optional[str] = None,
        description1: Optional[str] = None,
        section2: Optional[str] = None,
        description2: Optional[str] = None,
        section3: Optional[str] = None,
        description3: Optional[str] = None,
        couleur: Optional[str] = "blue",  # blue, green, red, orange, purple
        ping_role: Optional[str] = None,  # DEV, IA, INFRA, ALL
        image_url: Optional[str] = None,
        footer: Optional[str] = None,
    ):
        """Créer une annonce avec format enrichi"""
        await interaction.response.defer(ephemeral=True)

        # Définir la couleur
        colors = {
            "blue": discord.Color.blue(),
            "green": discord.Color.green(),
            "red": discord.Color.red(),
            "orange": discord.Color.orange(),
            "purple": discord.Color.purple(),
            "gold": discord.Color.gold(),
        }
        color = colors.get(couleur.lower(), discord.Color.blue())

        # Créer l'embed
        embed = discord.Embed(
            title=f"📢 {titre}", color=color, timestamp=discord.utils.utcnow()
        )

        # Ajouter les sections
        sections = [
            (section1, description1),
            (section2, description2),
            (section3, description3),
        ]

        for i, (section, description) in enumerate(sections, 1):
            if section:
                # Formatage différent selon la position
                if i == 1 and description:
                    # Section principale avec description
                    embed.add_field(
                        name=f"__**{section}**__", value=description, inline=False
                    )
                elif i == 1:
                    # Section principale sans description (en gras dans la description de l'embed)
                    embed.description = f"**{section}**"
                elif description:
                    # Sections secondaires avec description
                    embed.add_field(
                        name=f"**{section}**", value=description, inline=False
                    )
                else:
                    # Sections secondaires sans description
                    if embed.description:
                        embed.description += f"\n\n**{section}**"
                    else:
                        embed.description = f"**{section}**"

        # Ajouter l'image si fournie
        if image_url:
            embed.set_image(url=image_url)

        # Footer personnalisé ou par défaut
        if footer:
            embed.set_footer(text=footer, icon_url=interaction.user.display_avatar.url)
        else:
            embed.set_footer(
                text=f"LCSP - Par {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )

        # Déterminer les mentions
        mentions = []
        if ping_role:
            if ping_role.upper() == "ALL":
                mentions.append("@everyone")
            else:
                roles = [r.strip().upper() for r in ping_role.split(",")]
                for role_name in roles:
                    role = discord.utils.get(interaction.guild.roles, name=role_name)
                    if role:
                        mentions.append(role.mention)

        # Envoyer l'annonce
        await interaction.channel.send(
            content=" ".join(mentions) if mentions else None, embed=embed
        )

        await interaction.followup.send(
            "✅ Annonce publiée avec succès!", ephemeral=True
        )

    @app_commands.command(
        name="announce_simple", description="Faire une annonce simple (titre + message)"
    )
    @is_admin()
    async def announce_simple(
        self,
        interaction: discord.Interaction,
        titre: str,
        message: str,
        ping: Optional[bool] = False,
    ):
        """Annonce simple pour les messages rapides"""
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=f"📢 {titre}",
            description=message,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(
            text=f"LCSP - {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )

        content = "@everyone" if ping else None
        await interaction.channel.send(content=content, embed=embed)
        await interaction.followup.send("✅ Annonce envoyée", ephemeral=True)

    @app_commands.command(name="clear", description="Supprimer des messages")
    @is_admin()
    async def clear(
        self,
        interaction: discord.Interaction,
        nombre: int,
        user: Optional[discord.Member] = None,
    ):
        """Supprimer un certain nombre de messages"""
        await interaction.response.defer(ephemeral=True)

        if nombre < 1 or nombre > 100:
            await interaction.followup.send(
                "❌ Le nombre doit être entre 1 et 100", ephemeral=True
            )
            return

        # Supprimer les messages
        deleted = []
        if user:
            # Supprimer uniquement les messages de l'utilisateur spécifié
            def check(m):
                return m.author == user

            deleted = await interaction.channel.purge(limit=nombre, check=check)
        else:
            deleted = await interaction.channel.purge(limit=nombre)

        await interaction.followup.send(
            f"✅ {len(deleted)} messages supprimés", ephemeral=True
        )

    @app_commands.command(name="info", description="Informations sur le serveur")
    @is_admin()
    async def server_info(self, interaction: discord.Interaction):
        """Afficher les informations du serveur"""
        await interaction.response.defer()

        guild = interaction.guild

        # Créer l'embed
        embed = discord.Embed(
            title=f"ℹ️ Informations - {guild.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Statistiques générales
        embed.add_field(
            name="📊 Statistiques",
            value=f"Membres: {guild.member_count}\n"
            f"Rôles: {len(guild.roles)}\n"
            f"Canaux: {len(guild.channels)}",
            inline=True,
        )

        # Rôles techniques
        tech_roles = ["DEV", "IA", "INFRA"]
        role_counts = {}
        for role_name in tech_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                role_counts[role_name] = len(role.members)

        if role_counts:
            embed.add_field(
                name="👥 Répartition des pôles",
                value="\n".join(
                    f"{name}: {count}" for name, count in role_counts.items()
                ),
                inline=True,
            )

        # Informations de création
        embed.add_field(
            name="📅 Création", value=guild.created_at.strftime("%d/%m/%Y"), inline=True
        )

        # Propriétaire
        embed.add_field(
            name="👑 Propriétaire",
            value=guild.owner.mention if guild.owner else "Non défini",
            inline=True,
        )

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
