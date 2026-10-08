import os

USER_DATA_DIR = "/tmp/chrome_session"
DOWNLOAD_DIR = "/tmp/downloads"
EXTRACT_DIR = "/tmp/extracted"

# URL pour l'authentification initiale (domaine Google)
AUTH_URL = "https://drive.google.com/drive/folders/1-k3I8mLFdWHz_QDTqScfHvdREBWTUFCT"

# URL via proxy Netskope (navigation et extraction)
DRIVE_ROOT_URL = "https://drive.google.com.rproxy.goskope.com/drive/folders/1-k3I8mLFdWHz_QDTqScfHvdREBWTUFCT"