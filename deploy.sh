#!/bin/bash

echo "🚀 Déploiement du Bot LCSP Administratif"
echo "================================"

# Couleurs pour l'output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les erreurs
error_exit() {
    echo -e "${RED}❌ ERREUR: $1${NC}" >&2
    exit 1
}

# Fonction pour afficher les succès
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Fonction pour afficher les warnings
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Vérifier que Docker est installé
echo "1️⃣ Vérification de Docker..."
if ! command -v docker &> /dev/null; then
    error_exit "Docker n'est pas installé. Installez Docker d'abord."
fi
if ! command -v docker compose &> /dev/null; then
    error_exit "Docker Compose n'est pas installé."
fi
success "Docker et Docker Compose détectés"

# Vérifier le fichier .env
echo "2️⃣ Configuration de l'environnement..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        warning "Fichier .env manquant, copie depuis .env.example"
        cp .env.example .env
        echo ""
        echo "⚠️  IMPORTANT: Éditez le fichier .env avec vos vraies valeurs:"
        echo "   nano .env"
        echo ""
        read -p "Appuyez sur Entrée après avoir configuré le .env..."
    else
        error_exit "Aucun fichier .env ou .env.example trouvé!"
    fi
fi

# Vérifier que le token Discord est configuré
if grep -q "YOUR_BOT_TOKEN_HERE" .env; then
    error_exit "Le token Discord n'est pas configuré dans .env!"
fi
success "Configuration .env détectée"

# Arrêter les conteneurs existants
echo "3️⃣ Arrêt des conteneurs existants..."
docker compose down 2>/dev/null || true
success "Conteneurs arrêtés"

# Construire les images
echo "4️⃣ Construction des images Docker..."
if ! docker compose build; then
    error_exit "Échec de la construction des images"
fi
success "Images construites"

# Démarrer les services
echo "5️⃣ Démarrage des services..."
if ! docker compose up -d; then
    error_exit "Échec du démarrage des services"
fi
success "Services démarrés"

# Attendre que les services soient prêts
echo "6️⃣ Vérification de l'état des services..."
sleep 5

# Vérifier PostgreSQL
if docker compose exec -T postgres pg_isready &>/dev/null; then
    success "PostgreSQL est opérationnel"
else
    warning "PostgreSQL n'est pas encore prêt, vérifiez les logs"
fi

# Vérifier le bot
if docker compose ps | grep -q "lcsp.*Up"; then
    success "Bot Discord est en cours d'exécution"
else
    warning "Le bot n'est pas encore démarré, vérifiez les logs"
fi

# Mettre les permissions sur le fichier logs 
chmod 777 logs
success "Permissions données aux logs"

# Afficher les logs
echo ""
echo "7️⃣ Derniers logs du lcsp_admin_bot:"
echo "------------------------"
docker compose logs --tail=20 lcsp_admin_bot

echo ""
echo "================================"
success "Déploiement terminé!"
echo ""
echo "📝 Commandes utiles:"
echo "  • Voir les logs:        docker compose logs -f nom/id conteneur"
echo "  • Redémarrer le bot:    docker compose restart nom/id conteneur"
echo "  • Arrêter tout:         docker compose down"
echo "  • État des services:    docker compose ps"
echo "  • Backup DB:           docker compose exec postgres pg_dump -U lcsp_admin lcsp_db > backup.sql"
echo ""