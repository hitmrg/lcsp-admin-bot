# Cog Admin (cogs/admin.py)

import discord
from discord.ext import commands
from discord import app_commands
import logging
from config import ADMIN_ROLES
from database import Database

logger = logging.getLogger(__name__)


# Cog d'administration
class AdminCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Permet de vérifier si l'utilisateur qui exécute la commande est un admin
    # Pour cela il vérifie si l'utilisateur a un des rôles dans ADMIN_ROLES
    def is_admin():
        async def predicate(interaction: discord.Interaction):
            member = interaction.user

            if not isinstance(member, discord.Member):
                member = interaction.guild.get_member(interaction.user.id)

            if not member:
                logger.warning(
                    f"[ADMIN CHECK] Aucun membre trouvé pour {interaction.user}"
                )
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

    # --- Commandes d'administration ---
    # Permet de setup tout les éléments de base du serveur
    @app_commands.command(name="setup", description="Initialiser le serveur")
    @is_admin()
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.defer()

        guild = interaction.guild
        created = []

        # Créer les rôles s'ils n'existent pas
        roles_to_create = ["DEV", "IA", "INFRA"]
        for role_name in roles_to_create:
            if not discord.utils.get(guild.roles, name=role_name):
                await guild.create_role(name=role_name)
                created.append(f"Rôle: {role_name}")

        # Créer les canaux
        category = await guild.create_category("👑 ADMINISTRATION")
        await guild.create_text_channel("╭🔑・logs", category=category)
        await guild.create_text_channel("╭📑・documents", category=category)
        created.extend(
            [
                "Catégorie: 👑 ADMINISTRATION",
                "Canal: ╭🔑・logs",
                "Canal: ╭📑・documents",
            ]
        )

        embed = discord.Embed(
            title="✅ Configuration terminée",
            description="\n".join(f"• {item}" for item in created),
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=embed)

    # Permet de faire une annonce dans le canal dans lequel la commande est éxécutée
    @app_commands.command(name="announce", description="Faire une annonce")
    @is_admin()
    async def announce(
        self, interaction: discord.Interaction, titre: str, message: str
    ):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=f"📢 {titre}",
            description=message,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"Par {interaction.user.display_name}")

        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Annonce envoyée", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
