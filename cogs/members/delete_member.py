import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import Database
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class DeleteMember(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Supprimer un membre
    @app_commands.command(name="membre_delete", description="Supprimer un membre")
    @app_commands.describe(user="Utilisateur Discord du membre")
    @is_admin()
    async def delete_member(
        self, interaction: discord.Interaction, user: discord.Member
    ):
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
        
        logger.info(f"🗑️ Membre supprimé: {user} par {interaction.user}")

async def setup(bot):
    await bot.add_cog(DeleteMember(bot))