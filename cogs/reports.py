# Cog Rapports (cogs/reports.py)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime, timedelta
import io
import csv
from database import Database
from models import MemberStatus

class ReportsCog(commands.Cog):
    """Génération de rapports et statistiques"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="stats", description="Statistiques du laboratoire")
    async def stats(self, interaction: discord.Interaction):
        """Afficher les statistiques générales"""
        await interaction.response.defer()
        
        # Récupérer les données
        members = self.db.get_all_members()
        active = sum(1 for m in members if m.status == MemberStatus.ACTIVE)
        meetings = self.db.get_upcoming_meetings()
        
        embed = discord.Embed(
            title="📊 Statistiques CyberLab",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="👥 Membres",
            value=f"Total: {len(members)}\nActifs: {active}",
            inline=True
        )
        
        embed.add_field(
            name="📅 Réunions",
            value=f"À venir: {len(meetings)}",
            inline=True
        )
        
        # Top membres (exemple simplifié)
        embed.add_field(
            name="🏆 Membres actifs",
            value="Calcul en cours...",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="rapport", description="Rapport d'activité")
    async def report(
        self,
        interaction: discord.Interaction,
        jours: Optional[int] = 30
    ):
        """Générer un rapport d'activité"""
        await interaction.response.defer()
        
        embed = discord.Embed(
            title=f"📋 Rapport d'activité ({jours} jours)",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        # Statistiques générales
        members = self.db.get_all_members(status=MemberStatus.ACTIVE)
        
        # Calculer les taux de présence moyens
        total_rate = 0
        for member in members:
            stats = self.db.get_member_stats(member.id, days=jours)
            total_rate += stats['rate']
        
        avg_rate = total_rate / len(members) if members else 0
        
        embed.add_field(
            name="📈 Vue d'ensemble",
            value=f"Membres actifs: {len(members)}\nTaux présence moyen: {avg_rate:.1f}%",
            inline=False
        )
        
        # Identifier les membres inactifs
        inactive = []
        threshold = datetime.utcnow() - timedelta(days=14)
        for member in members:
            if member.last_active < threshold:
                inactive.append(member.username)
        
        if inactive:
            embed.add_field(
                name="⚠️ Membres inactifs",
                value=", ".join(inactive[:10]),
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="export", description="Exporter les données")
    async def export(self, interaction: discord.Interaction):
        """Exporter les données en CSV"""
        await interaction.response.defer(ephemeral=True)
        
        # Créer le CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow(['ID', 'Username', 'Nom', 'Email', 'Rôle', 'Statut'])
        
        # Données
        members = self.db.get_all_members()
        for member in members:
            writer.writerow([
                member.id,
                member.username,
                member.full_name or '',
                member.email or '',
                member.role or '',
                member.status.value
            ])
        
        # Créer le fichier
        csv_data = output.getvalue()
        file = discord.File(
            io.BytesIO(csv_data.encode()),
            filename=f"export_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        
        await interaction.followup.send(
            "📊 Export généré",
            file=file,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(ReportsCog(bot))