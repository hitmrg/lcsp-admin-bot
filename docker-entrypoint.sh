#!/bin/bash
set -e

echo "🚀 Démarrage du Bot LCSP Administratif..."
echo "================================"

# Afficher les variables d'environnement (sans les secrets)
echo "📊 Configuration:"
echo "   DB_HOST: ${DB_HOST}"
echo "   DB_PORT: ${DB_PORT}"
echo "   DB_NAME: ${DB_NAME}"
echo "   DB_USER: ${DB_USER}"
echo "   DATABASE_URL configuré: $([ ! -z "$DATABASE_URL" ] && echo "Oui" || echo "Non")"

# Attendre que PostgreSQL soit prêt
echo ""
echo "⏳ En attente de PostgreSQL..."
max_retries=30
counter=0

while [ $counter -lt $max_retries ]; do
    if PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "postgres" -c '\q' 2>/dev/null; then
        echo "✅ PostgreSQL est prêt!"
        break
    fi
    
    counter=$((counter+1))
    if [ $counter -eq $max_retries ]; then
        echo "❌ Impossible de se connecter à PostgreSQL après ${max_retries} tentatives"
        exit 1
    fi
    
    echo "   Tentative $counter/$max_retries..."
    sleep 2
done

# Créer la base de données si elle n'existe pas
echo ""
echo "🔧 Vérification de la base de données..."
if ! PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
    echo "   Création de la base de données ${DB_NAME}..."
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "postgres" -c "CREATE DATABASE ${DB_NAME};"
    echo "   ✅ Base de données créée"
else
    echo "   ✅ Base de données existante"
fi

# Initialiser/mettre à jour les tables
echo ""
echo "📋 Initialisation des tables..."
python -c "
import sys
try:
    from models import init_database
    if init_database():
        print('   ✅ Tables initialisées')
    else:
        print('   ❌ Erreur lors de l\'initialisation des tables')
        sys.exit(1)
except Exception as e:
    print(f'   ❌ Erreur: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Échec de l'initialisation de la base de données"
    exit 1
fi

# Vérifier la connexion Discord
echo ""
echo "🔍 Vérification du token Discord..."
python -c "
import os
import sys
token = os.getenv('DISCORD_TOKEN')
if not token or len(token) < 50:
    print('   ❌ Token Discord invalide ou manquant!')
    sys.exit(1)
print('   ✅ Token Discord détecté')
"

if [ $? -ne 0 ]; then
    echo "❌ Configuration Discord invalide"
    exit 1
fi

# Lancer le bot
echo ""
echo "================================"
echo "🤖 Lancement du bot..."
echo ""
exec python main.py