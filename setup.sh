#!/bin/bash
set -e

echo "=================================================="
echo "  INITIALISATION DE L'ENVIRONNEMENT (EXTRACTOR)   "
echo "=================================================="

# 1. Détection de l'interpréteur Python
if command -v python3 &> /dev/null && python3 -c "import sys" &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v py &> /dev/null && py -c "import sys" &> /dev/null; then
    PYTHON_CMD="py"
elif command -v python &> /dev/null && python -c "import sys" &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "\n[ERREUR] Aucun interpréteur Python valide n'a été trouvé."
    exit 1
fi

echo -e "\n[1/4] Interprèteur Python : $PYTHON_CMD"

# 2. Création et activation du venv
if [ ! -d "venv" ]; then
    echo -e "\n[2/4] Création de l'environnement virtuel 'venv'..."
    $PYTHON_CMD -m venv venv
else
    echo -e "\n[2/4] L'environnement 'venv' existe déjà."
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# 3. Installation des dépendances
echo -e "\n[3/4] Installation des dépendances Python..."
if [ -f "wheels.tar.gz" ] && [ ! -d "wheels" ]; then
    echo "    Extraction automatique de wheels.tar.gz..."
    tar -xzvf wheels.tar.gz
fi

if [ -d "wheels" ]; then
    echo "    Mode HORS-LIGNE : installation depuis ./wheels..."
    pip install --no-index --find-links=./wheels -r requirements.txt
else
    echo "    Mode EN LIGNE : installation standard via pip..."
    pip install -r requirements.txt
fi

# Installateur Playwright si présent
python -m playwright install chromium 2>/dev/null || true

# 4. Création des dossiers de travail
echo -e "\n[4/4] Création des dossiers de stockage..."
mkdir -p downloads tmp/chrome_session tmp/extracted 2>/dev/null || true

echo -e "\n=================================================="
echo " Environnement prêt !"
echo " Lance l'extraction avec : python main.py"
echo "=================================================="