import os
import time
import json
from playwright.sync_api import sync_playwright
import config
from modules.drive_collector import (
    normalize_fleet,
    normalize_ata,
    navigate_into_subfolder,
    download_subcontent_by_id
)

os.environ["DISPLAY"] = ":99"

def enable_chrome_auto_downloads(user_data_dir: str):
    """Force Chrome à autoriser les téléchargements multiples sans demander d'confirmation."""
    pref_path = os.path.join(user_data_dir, "Default", "Preferences")
    os.makedirs(os.path.dirname(pref_path), exist_ok=True)
    prefs = {}
    if os.path.exists(pref_path):
        try:
            with open(pref_path, "r") as f:
                prefs = json.load(f)
        except Exception:
            pass
    
    if "profile" not in prefs:
        prefs["profile"] = {}
    if "default_content_setting_values" not in prefs["profile"]:
        prefs["profile"]["default_content_setting_values"] = {}
    
    prefs["profile"]["default_content_setting_values"]["automatic_downloads"] = 1
    
    with open(pref_path, "w") as f:
        json.dump(prefs, f)

def prompt_user_inputs() -> dict:
    print("==================================================")
    print("      DRIVE STEP-BY-STEP NAVIGATION TEST          ")
    print("==================================================\n")

    raw_fleet = input("Enter Fleet (e.g. A320, A350): ").strip()
    fleet = normalize_fleet(raw_fleet)

    raw_ata = input("Enter ATA Chapter (e.g. 21, ATA21): ").strip()
    ata = normalize_ata(raw_ata)

    alert_title = input("Enter Alert Title / Description: ").strip()

    print("\n--- RESOLVED PARAMETERS ---")
    print(f"  * Fleet Family : {fleet}")
    print(f"  * Workspace    : 00_Model Workspace")
    print(f"  * ATA Chapter  : {ata}")
    print(f"  * Target Alert : {alert_title}")
    print("---------------------------\n")

    return {
        "fleet": fleet,
        "workspace": "00_Model Workspace",
        "ata": ata,
        "alert_title": alert_title
    }

def test_step_by_step_navigation():
    enable_chrome_auto_downloads(config.USER_DATA_DIR)
    params = prompt_user_inputs()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            headless=False,
            accept_downloads=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-popup-blocking",
                "--safebrowsing-disable-download-protection"
            ]
        )
        page = context.new_page()

        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        cdp = page.context.new_cdp_session(page)
        cdp.send("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": config.DOWNLOAD_DIR
        })

        print(f"[STEP 0/4] Ouverture du dossier racine Drive :\n{config.DRIVE_ROOT_URL}")
        page.goto(config.DRIVE_ROOT_URL)

        print(f"\n[STEP 1/4] Navigation Flotte : '{params['fleet']}'...")
        success, _ = navigate_into_subfolder(page, params['fleet'], is_fuzzy=False)
        if not success:
            context.close()
            return

        print(f"\n[STEP 2/4] Navigation Workspace : '{params['workspace']}'...")
        success, _ = navigate_into_subfolder(page, params['workspace'], is_fuzzy=False)
        if not success:
            context.close()
            return

        print(f"\n[STEP 3/4] Navigation ATA : '{params['ata']}'...")
        success, _ = navigate_into_subfolder(page, params['ata'], is_fuzzy=False)
        if not success:
            context.close()
            return

        print(f"\n[STEP 4/4] Recherche Alerte : '{params['alert_title']}'...")
        success, final_folder_name = navigate_into_subfolder(page, params['alert_title'], is_fuzzy=True)
        if not success:
            context.close()
            return

        print(f"\n[SUCCESS] Dossier cible ouvert : '{final_folder_name}'")

        # Extraction directe basée sur les identifiants de dossier uniques
        download_subcontent_by_id(page, config.DOWNLOAD_DIR)

        time.sleep(3)
        context.close()

if __name__ == "__main__":
    test_step_by_step_navigation()
