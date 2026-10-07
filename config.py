import os

# Parameters for Source 1 (Google Drive)
DRIVE_ROOT_URL = os.getenv("DRIVE_ROOT_URL", "https://drive.google.com/drive/folders/1A2b3C4d5E6f7G8h9I0J")
DRIVE_FILTRES = {
    "avion": "A320",
    "ata": "28",
    "sous_ata": "28-10",
    "model_id": "ATA21_PACK_LEAK_ACMS_M0"
}

# Web URL for Gemini or direct Gem link
GEMINI_WEB_URL = os.getenv("GEMINI_WEB_URL", "https://gemini.google.com/app")

# Temporary ephemeral storage on GCP Cloud Shell (/tmp)
DOWNLOAD_DIR = "/tmp/downloads"
EXTRACT_DIR = "/tmp/extracted"
USER_DATA_DIR = "/tmp/chrome_session"