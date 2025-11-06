import discord
from discord import app_commands
import logging
from config import ADMIN_ROLES

logger = logging.getLogger(__name__)

# Vérification que la personne qui tape la commande est administrateur
# CAD, qu'elle possède un des rôles dans ADMIN_ROLES (actuellement il n'y a que : *)
def is_admin():
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
