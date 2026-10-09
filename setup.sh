#!/bin/bash

set -e

echo "=========================================="
echo "  INITIALISATION DE L'ENVIRONNEMENT API  "
echo "=========================================="

# 1. Installation des dépendances Python (requests)
echo -e "\n[1/3] Installation des dépendances Python..."
pip install -r requirements.txt

# 2. Création des répertoires de travail
echo -e "\n[2/3] Préparation des dossiers temporaires..."
mkdir -p /tmp/downloads /tmp/extracted

# 3. Vérification et rafraîchissement de l'accès Google Drive
echo -e "\n[3/3] Authentification Google Drive via gcloud..."
gcloud auth login --enable-gdrive-access

echo -e "\n=========================================="
echo " Configuration terminée avec succès !"
echo " Tu peux maintenant lancer : python3 main.py"
echo "=========================================="