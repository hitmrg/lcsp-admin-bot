# Configuration (config.py)

import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', '0'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', '0'))

# Base de données
DB_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/cyberlab')

# Rôles autorisés
ADMIN_ROLES = ['ADMIN']
MEMBER_ROLES = ['INFRA', 'DEV', 'IA']

# Sécurité
BACKUP_RETENTION_DAYS = 30
SESSION_TIMEOUT = 300  # 5 minutes