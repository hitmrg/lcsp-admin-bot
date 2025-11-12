import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class AddMember(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Ajouter un membre
    @app_commands.command(name="membre_add", description="Ajouter un membre")
    @app_commands.describe(
        user="Utilisateur Discord du membre",
        nom="Nom complet du membre(Prénom.Initiale du nom)",
        pole="Pôle du membre (DEV, IA, INFRA)",
        email="Email du membre (optionnel)",
        specialisation="Spécialisation du membre (optionnel)",
    )
    @is_admin()
    async def add_member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nom: str,
        pole: Optional[str] = None,  # DEV, IA, INFRA
        email: Optional[str] = None,
        specialisation: Optional[str] = None,
    ):
        await interaction.response.defer()

        # Vérifier si le membre existe
        if self.db.get_member(str(user.id)):
            await interaction.followup.send(f"❌ {user.mention} est déjà enregistré")
            return

        valid_poles = ["DEV", "IA", "INFRA"]

        # Si un pôle est fourni, on valide
        if pole:
            pole = pole.upper()
            if pole not in valid_poles:
                await interaction.followup.send(
                    f"❌ Pôle invalide: {pole}\nPôles valides: {', '.join(valid_poles)}"
                )
                return
        # Si pole est None, on continue sans erreur

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

        logger.info(f"Membre ajouté: {user} ({member.id}) par {interaction.user}")


async def setup(bot):
    await bot.add_cog(AddMember(bot))
