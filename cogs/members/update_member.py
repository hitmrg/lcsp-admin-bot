import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from database import Database
from models import MemberStatus
from cogs.admin.is_admin import is_admin

logger = logging.getLogger(__name__)


class UpdateMember(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # Mettre à jour un membre
    @app_commands.command(name="membre_update", description="Modifier un membre")
    @app_commands.describe(
        user="Utilisateur Discord du membre",
        nom="Nouveau nom complet du membre (optionnel)",
        email="Nouvel email du membre (optionnel)",
        pole="Nouveau pôle du membre (DEV, IA, INFRA) (optionnel)",
        specialisation="Nouvelle spécialisation du membre (optionnel)",
        statut="Nouveau statut du membre (actif, inactif, suspendu) (optionnel)",
    )
    @is_admin()
    async def update_member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nom: Optional[str] = None,
        email: Optional[str] = None,
        pole: Optional[str] = None,
        specialisation: Optional[str] = None,
        statut: Optional[str] = None,  # actif, inactif, suspendu
    ):
        await interaction.response.defer(ephemeral=True)

        updates = {}
        if nom:
            updates["full_name"] = nom
        if email:
            updates["email"] = email
        if pole:
            pole = pole.upper()
            if pole not in ["DEV", "IA", "INFRA"]:
                await interaction.followup.send(
                    "❌ Pôle invalide. Utilisez: DEV, IA, INFRA", ephemeral=True
                )
                return
            updates["role"] = pole
        if specialisation:
            updates["specialization"] = specialisation
        if statut:
            statut_map = {
                "actif": MemberStatus.ACTIVE,
                "inactif": MemberStatus.INACTIVE,
                "suspendu": MemberStatus.SUSPENDED,
            }
            if statut.lower() not in statut_map:
                await interaction.followup.send(
                    "❌ Statut invalide. Utilisez: actif, inactif, suspendu",
                    ephemeral=True,
                )
                return
            updates["status"] = statut_map[statut.lower()]

        if not updates:
            await interaction.followup.send(
                "❌ Aucune modification spécifiée", ephemeral=True
            )
            return

        member = self.db.update_member(str(user.id), **updates)

        if member:
            # Mettre à jour le rôle Discord si nécessaire
            if pole:
                # Retirer les anciens rôles de pôle
                for role_name in ["DEV", "IA", "INFRA"]:
                    old_role = discord.utils.get(
                        interaction.guild.roles, name=role_name
                    )
                    if old_role and old_role in user.roles:
                        await user.remove_roles(old_role)

                # Ajouter le nouveau rôle
                new_role = discord.utils.get(interaction.guild.roles, name=pole)
                if new_role:
                    await user.add_roles(new_role)

            await interaction.followup.send(
                f"✅ {user.mention} mis à jour avec succès", ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ Membre non trouvé", ephemeral=True)
        
        logger.info(f"👤 Membre mis à jour: {user} par {interaction.user}")

async def setup(bot):
    await bot.add_cog(UpdateMember(bot))