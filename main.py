## Fichier principal (main.py)

import discord
from discord.ext import commands
import logging
import asyncio
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("lcsp_bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger("LCSP_BOT_ADMIN")

# Intents Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# Bot Administratif LCSP
class LCSPBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!", intents=intents, description="Bot administratif LCSP"
        )

    # Initialisation du bot
    async def setup_hook(self):
        # Charger les cogs
        cogs = ["cogs.admin", "cogs.members", "cogs.meetings", "cogs.reports"]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Cog chargé: {cog}")
            except Exception as e:
                logger.error(f"❌ Erreur chargement {cog}: {e}")

        # Synchroniser les commandes slash
        try:
            synced = await self.tree.sync()
            logger.info(f"🔄 {len(synced)} commandes synchronisées")
        except Exception as e:
            logger.error(f"❌ Erreur synchronisation: {e}")

    # Evènement de démarrage quand le bot est prêt
    async def on_ready(self):
        logger.info(f"🤖 {self.user} connecté!")
        logger.info(f"📊 Serveurs: {len(self.guilds)}")

        # Définir le statut du bot
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="le Laboratoire LCSP 🔬"
            ),
            status=discord.Status.online,
        )

    # Gestion des erreurs de commande (permission, arguments, etc.)
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argument manquant: {error.param.name}")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ Vous n'avez pas les permissions nécessaires")
        else:
            logger.error(f"Erreur non gérée: {error}")
            await ctx.send("❌ Une erreur est survenue")

    # Événement lors de l'ajout du bot à un serveur
    async def on_guild_join(self, guild):
        logger.info(f"➕ Ajouté au serveur: {guild.name} (ID: {guild.id})")

        # Envoyer un message de bienvenue au propriétaire
        if guild.owner:
            try:
                embed = discord.Embed(
                    title="🎉 Merci d'avoir ajouté le bot LCSP!",
                    description="Bot administratif du Laboratoire de Cybersécurité SUPINFO Paris",
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="🚀 Pour commencer",
                    value="Utilisez `/setup` pour initialiser le serveur",
                    inline=False,
                )
                embed.add_field(
                    name="❓ Aide",
                    value="Tapez `/` pour voir toutes les commandes disponibles",
                    inline=False,
                )
                await guild.owner.send(embed=embed)
            except:
                pass

    # Événement lors de l'arrivée d'un nouveau membre
    async def on_member_join(self, member):
        # Log
        logger.info(f"👤 Nouveau membre: {member} dans {member.guild}")

        # Message de bienvenue
        welcome_channel = discord.utils.get(
            member.guild.channels, name="╭👋・bienvenue"
        )
        if welcome_channel:
            embed = discord.Embed(
                title=f"👋 Bienvenue au LCSP!",
                description=f"Bienvenue {member.mention} au Laboratoire de Cybersécurité SUPINFO Paris!",
                color=discord.Color.blue(),
            )
            embed.add_field(
                name="📋 Prochaine étape",
                value="Un administrateur va t'enregistrer dans la base de données du laboratoire.",
                inline=False,
            )
            embed.add_field(
                name="🏛️ Pôles disponibles",
                value="• **DEV** - Développement\n• **IA** - Intelligence Artificielle\n• **INFRA** - Infrastructure",
                inline=False,
            )
            embed.set_thumbnail(url=member.display_avatar.url)

            await welcome_channel.send(embed=embed)


# Fonction principale
# Lance le bot
async def main():
    # Vérifier le token
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("❌ Token Discord non trouvé dans les variables d'environnement!")
        return

    # Créer et lancer le bot
    bot = LCSPBot()

    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("❌ Token Discord invalide!")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")


if __name__ == "__main__":
    asyncio.run(main())
