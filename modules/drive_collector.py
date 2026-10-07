import os
import re
import time
import zipfile
import difflib
from playwright.sync_api import sync_playwright
import config

def normalize_fleet(fleet_input: str) -> str:
    """Standardizes fleet strings (e.g., 'A350' -> 'A350 family')."""
    clean = fleet_input.strip()
    if not clean.lower().endswith("family"):
        return f"{clean.upper()} family"
    return clean.title()

def normalize_ata(ata_input: str) -> str:
    """Standardizes ATA input (e.g., '36' -> 'ATA36')."""
    clean = ata_input.strip().upper()
    if not clean.startswith("ATA"):
        return f"ATA{clean}"
    return clean

KNOWN_ACRONYMS = {
    "precooler": "pce",
    "pre-cooler": "pce",
    "pre cooler": "pce",
    "exchanger": "pce",
    "bleed": "bleed",
    "pack": "pack",
    "valve": "prv",
    "sar": "sar"
}

def expand_acronyms(text: str) -> str:
    """Expands aeronautical acronyms and terms to improve fuzzy search matching."""
    lower = text.lower()
    for full_form, abbr in KNOWN_ACRONYMS.items():
        if full_form in lower:
            lower += f" {abbr}"
    if "pce" in lower and "leakage" in lower:
        lower += " pre-cooler exchanger"
    return lower

def find_best_folder_match(items_locator, target_title: str):
    """
    Finds the best matching Drive element using token overlap and sequence ratio.
    Integrates acronym expansion and ignores system/parent labels.
    """
    best_item = None
    best_folder_name = ""
    best_score = 0.0

    expanded_target = expand_acronyms(target_title)
    user_tokens = set(re.findall(r'\w+', expanded_target.lower()))

    ignored_names = {
        "name", "nom", "owner", "propriétaire", "modified", "type",
        "size", "taille", "drive", "mon drive", "my drive", "workspace"
    }

    total_count = items_locator.count()
    for i in range(total_count):
        item = items_locator.nth(i)
        raw_text = item.inner_text().strip()
        folder_name = raw_text.splitlines()[0] if raw_text else ""
        if not folder_name:
            continue

        if folder_name.lower() in ignored_names or folder_name.lower().startswith("ata"):
            continue

        expanded_folder = expand_acronyms(folder_name)
        folder_tokens = set(re.findall(r'\w+', expanded_folder.lower()))

        token_score = len(user_tokens.intersection(folder_tokens)) / max(len(user_tokens), 1)
        seq_score = difflib.SequenceMatcher(None, expanded_target.lower(), expanded_folder.lower()).ratio()
        combined_score = (token_score * 0.6) + (seq_score * 0.4)

        if combined_score > best_score:
            best_score = combined_score
            best_item = item
            best_folder_name = folder_name

    return best_item, best_folder_name, best_score

def wait_and_check_drive_loaded(page) -> bool:
    """Verifies that the Google Drive container is hydrated and visible."""
    time.sleep(2)
    current_url = page.url

    if "accounts.google.com" in current_url or "signin" in current_url:
        print(f"\n[ERREUR AUTH] Redirection identifiée sur : {current_url}")
        return False

    try:
        page.wait_for_selector("div[role='main'], div[role='grid'], c-wiz", timeout=15000)
        return True
    except Exception:
        print(f"\n[ERREUR AFFICHAGE] Conteneur introuvable sur : {current_url}")
        return False

def navigate_into_subfolder(page, target_name: str, is_fuzzy: bool = False):
    """Enters a subfolder by double-clicking and pressing Enter."""
    if not wait_and_check_drive_loaded(page):
        return False, ""

    time.sleep(2)
    items = page.locator("div[role='row'], div[role='gridcell'], div[data-id]")
    item_count = items.count()
    if item_count == 0:
        print("   [ERROR] Aucun dossier détecté.")
        return False, ""

    if is_fuzzy:
        target_item, matched_name, score = find_best_folder_match(items, target_name)
        # Using a conservative threshold to prevent matching irrelevant projects
        if target_item and score >= 0.30:
            print(f"   [SUCCESS] Dossier d'alerte trouvé ({int(score * 100)}% correspondance) : '{matched_name}'")
            target_item.dblclick()
            time.sleep(0.5)
            page.keyboard.press("Enter")
            time.sleep(4)
            return True, matched_name
        else:
            print(f"   [ERROR] Aucune correspondance fiable pour '{target_name}' (meilleur score: {int(score * 100)}%).")
            return False, ""
    else:
        for i in range(item_count):
            item = items.nth(i)
            raw_text = item.inner_text().strip()
            folder_name = raw_text.splitlines()[0] if raw_text else ""
            if target_name.lower() in folder_name.lower():
                print(f"   [SUCCESS] Dossier trouvé : '{folder_name}'")
                item.dblclick()
                time.sleep(0.5)
                page.keyboard.press("Enter")
                time.sleep(3)
                return True, folder_name

        print(f"   [ERROR] Dossier '{target_name}' introuvable.")
        return False, ""

def is_drive_folder(row_locator, item_name: str) -> bool:
    """Determines whether a Drive element represents a subfolder or a downloadable file."""
    aria = (row_locator.get_attribute("aria-label") or "").lower()
    text = (row_locator.inner_text() or "").lower()

    known_extensions = (
        '.pdf', '.py', '.json', '.csv', '.xlsx', '.xls',
        '.doc', '.docx', '.txt', '.zip', '.tar', '.gz',
        '.png', '.jpg', '.jpeg', '.ipynb', '.yaml', '.yml', '.parquet'
    )
    if any(item_name.lower().endswith(ext) for ext in known_extensions):
        return False

    file_keywords = [
        "fichier", "file", "feuille de calcul", "spreadsheet", "hoja de cálculo",
        "document", "présentation", "presentation", "pdf", "tableur"
    ]
    if any(k in aria for k in file_keywords) or any(k in text for k in ["feuille de calcul", "hoja de cálculo", "google sheets"]):
        return False

    if any(k in aria for k in ["dossier", "folder"]):
        return True

    if row_locator.locator("svg[data-mime-type*='folder'], svg[aria-label*='ossier'], svg[aria-label*='older']").count() > 0:
        return True

    return "." not in item_name

def download_single_file(page, row_locator, target_dir: str, file_name: str) -> bool:
    """Downloads a single file using the toolbar button, context menu, or Shift+D."""
    os.makedirs(target_dir, exist_ok=True)
    existing_files = set(os.listdir(target_dir))

    try:
        row_locator.scroll_into_view_if_needed()
        time.sleep(0.3)
        row_locator.click()
        time.sleep(0.4)
    except Exception as e:
        print(f"         [WARN] Impossible de sélectionner '{file_name}': {e}")
        return False

    toolbar_dl_btn = page.locator(
        "button[aria-label*='Download'], button[aria-label*='Télécharger'], "
        "div[data-tooltip*='Download'], div[data-tooltip*='Télécharger'], "
        "div[aria-label*='Download'], div[aria-label*='Télécharger']"
    )

    try:
        with page.expect_download(timeout=14000) as dl_info:
            if toolbar_dl_btn.count() > 0 and toolbar_dl_btn.first.is_visible():
                toolbar_dl_btn.first.click()
            else:
                row_locator.click(button="right")
                time.sleep(0.4)
                menu_dl = page.locator("div[role='menuitem']:has-text('Télécharger'), div[role='menuitem']:has-text('Download')")
                if menu_dl.count() > 0 and menu_dl.first.is_visible():
                    menu_dl.first.click()
                else:
                    page.keyboard.press("Escape")
                    time.sleep(0.2)
                    page.keyboard.press("Shift+D")

        download = dl_info.value
        dest_filename = download.suggested_filename or file_name
        dest_path = os.path.join(target_dir, dest_filename)
        download.save_as(dest_path)
        print(f"         [OK] Téléchargé : {dest_filename}")
        return True
    except Exception:
        # Check disk polling in case Chrome wrote directly
        start_time = time.time()
        while time.time() - start_time < 8:
            time.sleep(1)
            diff = set(os.listdir(target_dir)) - existing_files
            finished = [f for f in diff if not f.endswith('.crdownload') and not f.endswith('.tmp')]
            if finished:
                print(f"         [OK - Disque] {finished[0]}")
                return True

    print(f"         [WARN] Échec du téléchargement pour '{file_name}'")
    return False

def crawl_and_download_alert_tree(page, base_download_dir: str, params: dict = None):
    """
    Crawls starting from the Target Alert folder.
    Recursively descends into each subfolder (01_Scoping, 02_Feasibility, etc.)
    and downloads every file, preserving directory hierarchy.
    """
    print("\n==================================================")
    print("      EXTRACTION RÉCURSIVE DE L'ALERTE CIBLE      ")
    print("==================================================")

    base_domain = "https://drive.google.com.rproxy.goskope.com"
    os.makedirs(base_download_dir, exist_ok=True)

    current_url = page.url
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', current_url)
    if not match:
        print("[ERREUR] Impossible de déterminer l'identifiant du dossier cible.")
        return

    root_alert_id = match.group(1)
    print(f"Point de départ (Dossier Alerte ID) : {root_alert_id}\n")

    folder_queue = [(root_alert_id, "")]
    visited_ids = set()

    # Blacklist parent folders and breadcrumb items so we NEVER navigate upwards
    forbidden_names = {
        "name", "nom", "owner", "propriétaire", "modified", "type", "size", "taille",
        "drive", "mon drive", "my drive"
    }
    if params:
        if "fleet" in params:
            forbidden_names.add(params["fleet"].lower().strip())
        if "workspace" in params:
            forbidden_names.add(params["workspace"].lower().strip())
        if "ata" in params:
            forbidden_names.add(params["ata"].lower().strip())

    while folder_queue:
        current_folder_id, rel_path = folder_queue.pop(0)
        visited_ids.add(current_folder_id)

        current_display = rel_path if rel_path else "/"
        current_dest = os.path.join(base_download_dir, rel_path)
        os.makedirs(current_dest, exist_ok=True)

        print(f"\n---> Dossier en cours d'exploration : '{current_display}' (ID: {current_folder_id})")

        target_folder_url = f"{base_domain}/drive/folders/{current_folder_id}"
        if page.url != target_folder_url:
            page.goto(target_folder_url)
            time.sleep(2)

        wait_and_check_drive_loaded(page)
        time.sleep(2)

        # Scrape strictly from the main grid content
        grid_rows = page.locator("div[role='main'] div[role='grid'] div[role='row'][data-id]")
        count = grid_rows.count()
        if count == 0:
            grid_rows = page.locator("div[role='main'] div[role='row'][data-id]")
            count = grid_rows.count()

        files_to_download = []
        subfolders_to_visit = []
        seen_row_ids = set()

        for idx in range(count):
            row = grid_rows.nth(idx)
            data_id = row.get_attribute("data-id")
            raw_text = row.inner_text().strip()

            if not data_id or not raw_text or data_id in seen_row_ids:
                continue

            item_name = raw_text.splitlines()[0].strip()

            if item_name.lower() in forbidden_names or "family" in item_name.lower() or "workspace" in item_name.lower():
                continue
            if data_id == current_folder_id or (data_id == root_alert_id and rel_path != ""):
                continue

            seen_row_ids.add(data_id)

            if is_drive_folder(row, item_name):
                subfolders_to_visit.append((data_id, item_name))
            else:
                files_to_download.append((row, item_name))

        print(f"      Fichiers trouvés     : {len(files_to_download)} -> {[f[1] for f in files_to_download]}")
        print(f"      Sous-dossiers trouvés: {len(subfolders_to_visit)} -> {[s[1] for s in subfolders_to_visit]}")

        # 1. Download all files directly in this folder
        for file_row, file_name in files_to_download:
            print(f"      Téléchargement du fichier : '{file_name}'...")
            download_single_file(page, file_row, current_dest, file_name)
            time.sleep(0.5)

        # 2. Add detected subfolders to exploration queue
        for sub_id, sub_name in subfolders_to_visit:
            if sub_id not in visited_ids:
                next_rel_path = os.path.join(rel_path, sub_name)
                folder_queue.append((sub_id, next_rel_path))

    print(f"\n[SUCCÈS] Arborescence complète de l'alerte téléchargée dans : {base_download_dir}")

def unpack_all_archives(download_dir: str, extract_dir: str):
    """Uncompresses all zip files in download_dir to extract_dir."""
    os.makedirs(extract_dir, exist_ok=True)
    unpacked = []
    for root, _, files in os.walk(download_dir):
        for f in files:
            full_path = os.path.join(root, f)
            if f.lower().endswith(".zip"):
                try:
                    with zipfile.ZipFile(full_path, 'r') as z:
                        z.extractall(extract_dir)
                        unpacked.extend(z.namelist())
                except Exception as e:
                    print(f"Erreur décompression {f}: {e}")
            else:
                unpacked.append(f)
    print(f"\n[EXTRACTION] Total fichiers prêts dans {extract_dir}: {len(unpacked)} élément(s).")
    return unpacked