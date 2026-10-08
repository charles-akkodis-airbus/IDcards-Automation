import os
import time
import subprocess
import requests
from typing import Optional, Dict
import config

ROOT_FOLDER_ID = getattr(config, "ROOT_FOLDER_ID", "1-k3I8mLFdWHz_QDTqScfHvdREBWTUFCT")
DOWNLOAD_DIR = getattr(config, "DOWNLOAD_DIR", "/tmp/downloads")

def get_access_token() -> str:
    """Récupère le jeton d'accès OAuth actif via gcloud."""
    cmd = ["gcloud", "auth", "print-access-token"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout.strip()

def safe_api_get(url: str, headers: dict, params: dict, max_retries: int = 5) -> Optional[requests.Response]:
    """Effectue une requête GET avec gestion automatique des quotas (Exponential Backoff)."""
    delay = 3
    for attempt in range(max_retries):
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            return res
        elif res.status_code in [403, 429] and ("rateLimitExceeded" in res.text or "quota" in res.text.lower()):
            print(f"   [QUOTA ATTEINT] Pause de {delay}s ({attempt + 1}/{max_retries})...")
            time.sleep(delay)
            delay *= 2
        else:
            return res
    return None

def normalize_fleet(raw_fleet: str) -> str:
    clean = raw_fleet.strip()
    if not clean.lower().endswith("family"):
        return f"{clean} family"
    return clean

def normalize_ata(raw_ata: str) -> str:
    clean = raw_ata.strip().upper()
    if not clean.startswith("ATA"):
        return f"ATA{clean}"
    return clean

def search_subfolder(parent_id: str, target_name: str, fuzzy: bool = False) -> Optional[Dict[str, str]]:
    """Recherche un sous-dossier spécifique dans un dossier parent."""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    query = f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": query,
        "fields": "files(id, name)",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true"
    }

    res = safe_api_get(url, headers, params)
    if not res or res.status_code != 200:
        return None

    folders = res.json().get("files", [])
    target_clean = target_name.lower().strip()

    if not fuzzy:
        for f in folders:
            if f["name"].lower().strip() == target_clean or target_clean in f["name"].lower():
                return f
    else:
        words = [w for w in target_clean.split() if len(w) > 2]
        best_match = None
        best_score = 0.0
        for f in folders:
            f_name_lower = f["name"].lower()
            matches = sum(1 for w in words if w in f_name_lower)
            score = (matches / len(words)) if words else 0
            if score > best_score and score >= 0.4:
                best_score = score
                best_match = f
        if best_match:
            print(f"   [MATCH ALERTE {int(best_score*100)}%] Dossier sélectionné : « {best_match['name']} »")
            return best_match
    return None

def download_folder_files(folder_id: str, output_dir: str):
    """Exporte et télécharge les fichiers du dossier final."""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    os.makedirs(output_dir, exist_ok=True)

    query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": query,
        "fields": "files(id, name, mimeType)",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true"
    }

    res = safe_api_get(url, headers, params)
    if not res or res.status_code != 200:
        print("   [ERREUR API] Impossible de lister les fichiers du dossier cible.")
        return

    files = res.json().get("files", [])
    print(f"\nFichiers cibles identifiés : {len(files)}")

    export_formats = {
        "application/vnd.google-apps.presentation": (
            "https://www.googleapis.com/drive/v3/files/{}/export?mimeType=application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".pptx"
        ),
        "application/vnd.google-apps.spreadsheet": (
            "https://www.googleapis.com/drive/v3/files/{}/export?mimeType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xlsx"
        ),
        "application/vnd.google-apps.document": (
            "https://www.googleapis.com/drive/v3/files/{}/export?mimeType=application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".docx"
        )
    }

    for f in files:
        f_id, f_name, mime = f["id"], f["name"], f["mimeType"]
        if mime in export_formats:
            dl_url, ext = export_formats[mime]
            dl_url = dl_url.format(f_id)
            final_name = f_name if f_name.endswith(ext) else f"{f_name}{ext}"
        else:
            dl_url = f"https://www.googleapis.com/drive/v3/files/{f_id}?alt=media&supportsAllDrives=true"
            final_name = f_name

        print(f" -> Téléchargement : « {final_name} »...")
        time.sleep(1)
        file_res = requests.get(dl_url, headers=headers, stream=True)
        if file_res.status_code == 200:
            dest_path = os.path.join(output_dir, final_name)
            with open(dest_path, "wb") as out:
                for chunk in file_res.iter_content(chunk_size=8192):
                    out.write(chunk)
            print(f"    [OK] Fichier sauvegardé dans : {dest_path}")
        else:
            print(f"    [ERREUR {file_res.status_code}] Échec pour {f_name}")

def fetch_drive_files(params: dict) -> str:
    """Wrapper principal appelé par main.py."""
    print("==================================================")
    print("     NAVIGATION CIBLÉE VIA GOOGLE DRIVE API       ")
    print("==================================================")

    fleet = normalize_fleet(params.get("fleet_family", ""))
    workspace = params.get("workspace", "00_Model Workspace")
    ata = normalize_ata(params.get("ata_chapter", ""))
    alert = params.get("target_alert", "")
    output_dir = params.get("download_dir", DOWNLOAD_DIR)

    print(f"\n[1/4] Recherche Flotte : « {fleet} »...")
    fleet_folder = search_subfolder(ROOT_FOLDER_ID, fleet)
    if not fleet_folder:
        print("   [STOP] Flotte introuvable.")
        return output_dir
    time.sleep(1)

    print(f"\n[2/4] Recherche Workspace : « {workspace} »...")
    ws_folder = search_subfolder(fleet_folder['id'], workspace)
    if not ws_folder:
        print("   [STOP] Workspace introuvable.")
        return output_dir
    time.sleep(1)

    print(f"\n[3/4] Recherche ATA : « {ata} »...")
    ata_folder = search_subfolder(ws_folder['id'], ata)
    if not ata_folder:
        print("   [STOP] Dossier ATA introuvable.")
        return output_dir
    time.sleep(1)

    print(f"\n[4/4] Recherche Alerte : « {alert} »...")
    alert_folder = search_subfolder(ata_folder['id'], alert, fuzzy=True)
    if not alert_folder:
        print("   [STOP] Dossier d'alerte introuvable.")
        return output_dir

    download_folder_files(alert_folder['id'], output_dir)
    return output_dir