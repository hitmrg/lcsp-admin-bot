#!/bin/bash

echo "🔧 Correction des fins de ligne pour Windows/Git Bash"
echo "====================================================="

# Convertir tous les fichiers nécessaires
files=(
    "docker-entrypoint.sh"
    "deploy.sh"
    "fix-line-endings.sh"
    "Dockerfile"
    ".env"
    "*.py"
)

for file in "${files[@]}"; do
    if [ -e "$file" ] || ls $file 2>/dev/null; then
        echo "📝 Conversion: $file"
        # Utiliser sed pour convertir CRLF en LF
        sed -i 's/\r$//' $file 2>/dev/null || \
        sed -i '' 's/\r$//' $file 2>/dev/null || \
        echo "   ⚠️  Impossible de convertir $file"
    fi
done

# Rendre les scripts exécutables
chmod +x *.sh 2>/dev/null || true

echo ""
echo "✅ Conversion terminée!"
echo ""
echo "Vous pouvez maintenant lancer: ./deploy.sh"