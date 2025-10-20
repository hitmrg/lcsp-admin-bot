# Cog Réunions (cogs/meetings.py)

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime
import logging
from config import ADMIN_ROLES
from database import Database

logger = logging.getLogger(__name__)

class MeetingsCog(commands.Cog):
    """Gestion des réunions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.active_meetings = {}
    
    def is_admin():
        async def predicate(interaction: discord.Interaction):
            return any(role.name in ADMIN_ROLES for role in interaction.user.roles)
        return app_commands.check(predicate)
    
    @app_commands.command(name="meeting_create", description="Créer une réunion")
    @is_admin()
    async def create_meeting(
        self,
        interaction: discord.Interaction,
        titre: str,
        date: str,
        description: Optional[str] = None
    ):
        """Créer une nouvelle réunion"""
        await interaction.response.defer()
        
        # Parser la date (format: JJ/MM/AAAA HH:MM)
        try:
            meeting_date = datetime.strptime(date, "%d/%m/%Y %H:%M")
        except ValueError:
            await interaction.followup.send("❌ Format: JJ/MM/AAAA HH:MM")
            return
        
        # Créer la réunion
        meeting = self.db.create_meeting(
            title=titre,
            date=meeting_date,
            description=description,
            created_by=str(interaction.user.id)
        )
        
        embed = discord.Embed(
            title="✅ Réunion créée",
            color=discord.Color.green()
        )
        embed.add_field(name="Titre", value=titre)
        embed.add_field(name="Date", value=meeting_date.strftime("%d/%m/%Y %H:%M"))
        if description:
            embed.add_field(name="Description", value=description, inline=False)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="appel", description="Faire l'appel")
    @is_admin()
    async def start_attendance(
        self,
        interaction: discord.Interaction,
        meeting_id: int
    ):
        """Démarrer l'appel pour une réunion"""
        await interaction.response.defer()
        
        meeting = self.db.get_meeting(meeting_id)
        if not meeting:
            await interaction.followup.send("❌ Réunion introuvable")
            return
        
        # Créer l'embed d'appel
        embed = discord.Embed(
            title=f"📢 Appel - {meeting.title}",
            description="Cliquez sur ✅ pour marquer votre présence",
            color=discord.Color.blue()
        )
        
        # Créer la vue avec le bouton
        view = AttendanceView(meeting_id, self.db)
        message = await interaction.followup.send(embed=embed, view=view)
        
        self.active_meetings[meeting_id] = message
    
    @app_commands.command(name="meetings", description="Prochaines réunions")
    async def list_meetings(self, interaction: discord.Interaction):
        """Lister les prochaines réunions"""
        await interaction.response.defer()
        
        meetings = self.db.get_upcoming_meetings()
        
        if not meetings:
            await interaction.followup.send("Aucune réunion prévue")
            return
        
        embed = discord.Embed(
            title="📅 Prochaines réunions",
            color=discord.Color.blue()
        )
        
        for meeting in meetings:
            embed.add_field(
                name=f"#{meeting.id} - {meeting.title}",
                value=f"Date: {meeting.date.strftime('%d/%m/%Y %H:%M')}\n{meeting.description or ''}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)

class AttendanceView(discord.ui.View):
    """Vue pour l'appel"""
    
    def __init__(self, meeting_id, db):
        super().__init__(timeout=1800)  # 30 minutes
        self.meeting_id = meeting_id
        self.db = db
        self.attendees = set()
    
    @discord.ui.button(label="✅ Présent", style=discord.ButtonStyle.success)
    async def present(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Marquer sa présence"""
        member = self.db.get_member(str(interaction.user.id))
        
        if not member:
            await interaction.response.send_message(
                "❌ Vous n'êtes pas enregistré",
                ephemeral=True
            )
            return
        
        if interaction.user.id in self.attendees:
            await interaction.response.send_message(
                "✅ Déjà marqué présent",
                ephemeral=True
            )
            return
        
        self.db.record_attendance(self.meeting_id, member.id, 'present')
        self.attendees.add(interaction.user.id)
        
        await interaction.response.send_message(
            "✅ Présence enregistrée",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(MeetingsCog(bot))