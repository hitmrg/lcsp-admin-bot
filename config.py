import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

# Base de données - Construction sécurisée de l'URL
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "lcsp_db")
DB_USER = os.getenv("DB_USER", "lcsp_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Encoder le mot de passe pour éviter les problèmes avec les caractères spéciaux
if DB_PASSWORD:
    DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD)
else:
    DB_PASSWORD_ENCODED = ""

# Construire l'URL de manière sécurisée
if DB_PASSWORD:
    DB_URL = (
        f"postgresql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
else:
    DB_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Alternative : utiliser DATABASE_URL si fourni directement
DATABASE_URL = os.getenv("DATABASE_URL", DB_URL)

# Rôles autorisés
ADMIN_ROLES = ["*"]
MEMBER_ROLES = ["INFRA", "DEV", "IA"]

# Logging
print(f"📊 Configuration DB:")
print(f"   Host: {DB_HOST}")
print(f"   Port: {DB_PORT}")
print(f"   Database: {DB_NAME}")
print(f"   User: {DB_USER}")
print(f"   URL: postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")
