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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CyberLab')

# Intents Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class CyberLabBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
    async def setup_hook(self):
        # Charger les cogs
        cogs = ['cogs.admin', 'cogs.members', 'cogs.meetings', 'cogs.reports']
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Cog chargé: {cog}")
            except Exception as e:
                logger.error(f"❌ Erreur chargement {cog}: {e}")
        
        # Synchroniser les commandes slash
        await self.tree.sync()
        logger.info("🔄 Commandes synchronisées")
    
    # Evènement de démarrage
    async def on_ready(self):
        logger.info(f'🤖 {self.user} connecté!')
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="la sécurité du lab"
            )
        )

# Lancer le bot
async def main():
    bot = CyberLabBot()
    await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())