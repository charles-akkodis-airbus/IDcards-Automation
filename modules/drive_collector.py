import os
import re
import time
import zipfile
import difflib
from playwright.sync_api import sync_playwright
import config

def normalize_fleet(fleet_input: str) -> str:
    clean = fleet_input.strip()
    if not clean.lower().endswith("family"):
        return f"{clean.upper()} family"
    return clean.title()

def normalize_ata(ata_input: str) -> str:
    clean = ata_input.strip().upper()
    if not clean.startswith("ATA"):
        return f"ATA{clean}"
    return clean

def find_best_folder_match(items_locator, target_title: str):
    best_item = None
    best_folder_name = ""
    best_score = 0.0

    user_tokens = set(re.findall(r'\w+', target_title.lower()))

    for i in range(items_locator.count()):
        item = items_locator.nth(i)
        raw_text = item.inner_text().strip()
        folder_name = raw_text.splitlines()[0] if raw_text else ""

        if not folder_name:
            continue

        folder_tokens = set(re.findall(r'\w+', folder_name.lower()))
        token_score = len(user_tokens.intersection(folder_tokens)) / max(len(user_tokens), 1)
        seq_score = difflib.SequenceMatcher(None, target_title.lower(), folder_name.lower()).ratio()

        combined_score = (token_score * 0.6) + (seq_score * 0.4)

        if combined_score > best_score:
            best_score = combined_score
            best_item = item
            best_folder_name = folder_name

    return best_item, best_folder_name, best_score

def wait_and_check_drive_loaded(page) -> bool:
    time.sleep(3)
    current_url = page.url

    if "rproxy.goskope.com" in current_url:
        try:
            page.wait_for_selector("div[role='main'], div[role='grid'], c-wiz", timeout=15000)
            return True
        except Exception:
            pass

    if "accounts.google.com" in current_url or "signin" in current_url:
        print(f"\n[ERREUR AUTH] Redirection identifiée sur : {current_url}")
        page.screenshot(path="/tmp/auth_redirect.png")
        return False

    try:
        page.wait_for_selector("div[role='main'], div[role='grid'], c-wiz", timeout=15000)
        return True
    except Exception as e:
        print(f"\n[ERREUR AFFICHAGE] Conteneur introuvable sur : {current_url}")
        page.screenshot(path="/tmp/drive_nav_error.png")
        return False

def navigate_into_subfolder(page, target_name: str, is_fuzzy: bool = False):
    if not wait_and_check_drive_loaded(page):
        return False, ""

    time.sleep(2)
    items = page.locator("div[role='row'], div[role='gridcell'], div[data-id]")
    item_count = items.count()

    if item_count == 0:
        print("   [ERROR] Aucun sous-dossier détecté.")
        return False, ""

    if is_fuzzy:
        target_item, matched_name, score = find_best_folder_match(items, target_name)
        if target_item and score > 0.15:
            print(f"   [SUCCESS] Dossier d'alerte trouvé ({int(score * 100)}% correspondance) : '{matched_name}'")
            target_item.dblclick()
            time.sleep(0.5)
            page.keyboard.press("Enter")
            time.sleep(3)
            return True, matched_name
        else:
            print(f"   [ERROR] Impossible de faire correspondre '{target_name}'.")
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

        print(f"   [ERROR] Sous-dossier '{target_name}' introuvable.")
        return False, ""

def download_subcontent_by_id(page, download_dir: str):
    """
    Parcourt chaque élément par son identifiant unique data-id
    et attend le rendu complet des fichiers internes.
    """
    print("\n[EXTRACTION PAR ID] Analyse du contenu du dossier d'alerte...")
    time.sleep(4)
    os.makedirs(download_dir, exist_ok=True)

    raw_elements = page.locator("div[data-id]")
    count = raw_elements.count()

    folder_targets = []
    for i in range(count):
        el = raw_elements.nth(i)
        data_id = el.get_attribute("data-id")
        raw_text = el.inner_text().strip()

        if data_id and raw_text:
            name = raw_text.splitlines()[0]
            if name and name.lower() not in ["name", "nom", "owner", "modified", "type"]:
                folder_targets.append((name, data_id))

    unique_targets = list({item[1]: item for item in folder_targets}.values())
    print(f"Éléments détectés dans l'alerte ({len(unique_targets)}) : {[t[0] for t in unique_targets]}\n")

    base_domain = "https://drive.google.com.rproxy.goskope.com"

    for idx, (name, folder_id) in enumerate(unique_targets, 1):
        print(f"[{idx}/{len(unique_targets)}] Navigation vers : '{name}' (ID: {folder_id})...")
        
        target_url = f"{base_domain}/drive/folders/{folder_id}"
        page.goto(target_url)

        # Attente explicite que les éléments internes soient injectés dans le DOM
        try:
            page.wait_for_selector(
                "div[role='main'] div[role='row'], div[role='grid'] div[role='gridcell'], div[data-id]",
                timeout=12000
            )
            time.sleep(2)
        except Exception:
            print("   Attente du contenu expirée (dossier vide ou fichier unique).")

        # Recherche des lignes représentant des fichiers
        rows = page.locator("div[role='row'], div[data-id]")
        valid_items = []

        for k in range(rows.count()):
            txt = rows.nth(k).inner_text().strip()
            if txt:
                first_line = txt.splitlines()[0].lower()
                if first_line not in ["name", "nom", "owner", "modified", "size", "taille"]:
                    valid_items.append(rows.nth(k))

        if len(valid_items) > 0:
            print(f"   -> {len(valid_items)} fichier(s)/élément(s) trouvé(s) à l'intérieur.")
            existing_files = set(os.listdir(download_dir))

            # Focus et sélection
            valid_items[0].click()
            time.sleep(0.5)
            page.keyboard.press("Control+a")
            time.sleep(1)

            download_btn = page.locator(
                "button[aria-label*='Download'], button[aria-label*='Télécharger'], "
                "div[aria-label*='Download'], div[aria-label*='Télécharger'], "
                "div[data-tooltip*='Download'], div[data-tooltip*='Télécharger']"
            )

            if download_btn.count() > 0 and download_btn.first.is_visible():
                download_btn.first.click()
            else:
                page.keyboard.press("Shift+D")

            print("   └─ Demande de téléchargement transmise, attente écriture...")

            start_time = time.time()
            saved = False
            while time.time() - start_time < 45:
                time.sleep(2)
                current_files = set(os.listdir(download_dir))
                new_files = current_files - existing_files
                completed = [f for f in new_files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
                if completed:
                    print(f"   Téléchargé sur le disque : {completed[0]}")
                    saved = True
                    break

            if not saved:
                print("   Fichier non reçu ou traitement Google Drive prolongé.")
        else:
            print("   └─ Aucun fichier détecté dans cet élément.")

    print(f"\nDiagnostic et extraction terminés dans : {download_dir}")
