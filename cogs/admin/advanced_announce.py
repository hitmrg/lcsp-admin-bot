import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from .is_admin import is_admin

logger = logging.getLogger(__name__)

class AdvancedAnnounce(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Commande d'annonce avancée
    @app_commands.command(name="announce", description="Faire une annonce structurée")
    @app_commands.describe(
        ping_role="Rôle à mentionner (DEV, IA, INFRA, ALL)",
        couleur="Couleur de l'embed (blue, green, red, orange, purple, gold)",
        footer="Texte du footer de l'embed",
    )
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

# Fonction de setup du cog
async def setup(bot):
    await bot.add_cog(AdvancedAnnounce(bot))