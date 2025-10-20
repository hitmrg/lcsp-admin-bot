# Cog Admin (cogs/admin.py)

import discord
from discord.ext import commands
from discord import app_commands
import logging
from config import ADMIN_ROLES
from database import Database

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog):
    """Commandes d'administration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    def is_admin():
        """Vérifier les permissions admin"""
        async def predicate(interaction: discord.Interaction):
            return any(role.name in ADMIN_ROLES for role in interaction.user.roles)
        return app_commands.check(predicate)
    
    @app_commands.command(name="setup", description="Initialiser le serveur")
    @is_admin()
    async def setup(self, interaction: discord.Interaction):
        """Configurer les rôles et canaux nécessaires"""
        await interaction.response.defer()
        
        guild = interaction.guild
        created = []
        
        # Créer les rôles s'ils n'existent pas
        roles_to_create = ['Membre', 'Chercheur', 'Responsable']
        for role_name in roles_to_create:
            if not discord.utils.get(guild.roles, name=role_name):
                await guild.create_role(name=role_name)
                created.append(f"Rôle: {role_name}")
        
        # Créer les canaux
        category = await guild.create_category("CyberLab")
        await guild.create_text_channel("logs", category=category)
        await guild.create_text_channel("rapports", category=category)
        created.extend(["Catégorie: CyberLab", "Canal: logs", "Canal: rapports"])
        
        embed = discord.Embed(
            title="✅ Configuration terminée",
            description="\n".join(f"• {item}" for item in created),
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="purge", description="Nettoyer les messages")
    @is_admin()
    async def purge(self, interaction: discord.Interaction, nombre: int):
        """Supprimer des messages"""
        await interaction.response.defer(ephemeral=True)
        
        if nombre > 100:
            await interaction.followup.send("❌ Maximum 100 messages", ephemeral=True)
            return
        
        deleted = await interaction.channel.purge(limit=nombre)
        await interaction.followup.send(f"✅ {len(deleted)} messages supprimés", ephemeral=True)
    
    @app_commands.command(name="announce", description="Faire une annonce")
    @is_admin()
    async def announce(self, interaction: discord.Interaction, titre: str, message: str):
        """Envoyer une annonce"""
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title=f"📢 {titre}",
            description=message,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Par {interaction.user.display_name}")
        
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Annonce envoyée", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))