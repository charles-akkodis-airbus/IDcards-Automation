import os

# Répertoire racine du projet
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

USER_DATA_DIR = os.path.join(BASE_DIR, "tmp", "chrome_session")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
EXTRACT_DIR = os.path.join(BASE_DIR, "tmp", "extracted")

# ID racine du dossier Google Drive
ROOT_FOLDER_ID = "1-k3I8mLFdWHz_QDTqScfHvdREBWTUFCT"

# URL de l'interface Web Gemini
GEMINI_WEB_URL = "https://gemini.google.com"