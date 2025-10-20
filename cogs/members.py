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

class MembersCog(commands.Cog):
    """Gestion des membres"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    def is_admin():
        async def predicate(interaction: discord.Interaction):
            return any(role.name in ADMIN_ROLES for role in interaction.user.roles)
        return app_commands.check(predicate)
    
    @app_commands.command(name="membre_add", description="Ajouter un membre")
    @is_admin()
    async def add_member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nom: str,
        email: str,
        role: str
    ):
        """Ajouter un nouveau membre"""
        await interaction.response.defer()
        
        # Vérifier si le membre existe
        if self.db.get_member(str(user.id)):
            await interaction.followup.send(f"❌ {user.mention} est déjà enregistré")
            return
        
        # Ajouter le membre
        member = self.db.add_member(
            discord_id=str(user.id),
            username=user.name,
            full_name=nom,
            email=email,
            role=role
        )
        
        embed = discord.Embed(
            title="✅ Membre ajouté",
            color=discord.Color.green()
        )
        embed.add_field(name="Discord", value=user.mention)
        embed.add_field(name="Nom", value=nom)
        embed.add_field(name="Email", value=email)
        embed.add_field(name="Rôle", value=role)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="membre_info", description="Informations d'un membre")
    async def member_info(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ):
        """Voir les informations d'un membre"""
        await interaction.response.defer()
        
        target = user or interaction.user
        member = self.db.get_member(str(target.id))
        
        if not member:
            await interaction.followup.send(f"❌ {target.mention} non trouvé")
            return
        
        # Calculer les stats
        stats = self.db.get_member_stats(member.id)
        
        embed = discord.Embed(
            title=f"📋 {member.full_name or member.username}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Discord", value=f"<@{member.discord_id}>")
        embed.add_field(name="Email", value=member.email or "Non renseigné")
        embed.add_field(name="Rôle", value=member.role or "Non défini")
        embed.add_field(name="Statut", value=member.status.value)
        embed.add_field(name="Membre depuis", value=member.joined_at.strftime("%d/%m/%Y"))
        embed.add_field(name="Présence (30j)", value=f"{stats['rate']:.1f}%")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="membre_update", description="Modifier un membre")
    @is_admin()
    async def update_member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nom: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None
    ):
        """Modifier les informations d'un membre"""
        await interaction.response.defer(ephemeral=True)
        
        updates = {}
        if nom: updates['full_name'] = nom
        if email: updates['email'] = email
        if role: updates['role'] = role
        
        if not updates:
            await interaction.followup.send("❌ Aucune modification", ephemeral=True)
            return
        
        member = self.db.update_member(str(user.id), **updates)
        
        if member:
            await interaction.followup.send(f"✅ {user.mention} mis à jour", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Membre non trouvé", ephemeral=True)
    
    @app_commands.command(name="membre_delete", description="Supprimer un membre")
    @is_admin()
    async def delete_member(self, interaction: discord.Interaction, user: discord.Member):
        """Supprimer un membre"""
        await interaction.response.defer(ephemeral=True)
        
        if self.db.delete_member(str(user.id)):
            await interaction.followup.send(f"✅ {user.mention} supprimé", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Membre non trouvé", ephemeral=True)
    
    @app_commands.command(name="membres", description="Liste des membres")
    async def list_members(self, interaction: discord.Interaction):
        """Lister tous les membres"""
        await interaction.response.defer()
        
        members = self.db.get_all_members()
        
        if not members:
            await interaction.followup.send("Aucun membre enregistré")
            return
        
        embed = discord.Embed(
            title=f"👥 Membres ({len(members)})",
            color=discord.Color.blue()
        )
        
        for member in members[:25]:  # Discord limite à 25 fields
            embed.add_field(
                name=member.full_name or member.username,
                value=f"Rôle: {member.role or 'Non défini'}\nStatut: {member.status.value}",
                inline=True
            )
        
        if len(members) > 25:
            embed.set_footer(text=f"Et {len(members) - 25} autres...")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MembersCog(bot))