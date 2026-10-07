import os
import time
from playwright.sync_api import sync_playwright
import config

os.environ["DISPLAY"] = ":99"

def run_auth():
    print("Ouverture de Chrome sur le bureau virtuel (:99)...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        page = context.new_page()
        page.goto(config.DRIVE_ROOT_URL)

        print("\n" + "="*60)
        print("Une fois que tu vois les dossiers Google Drive à l'écran,")
        print("reviens ici et appuie sur ENTRÉE pour sauvegarder.")
        print("="*60 + "\n")

        input("Appuie sur ENTRÉE pour enregistrer la session...")

        print("Sauvegarde des jetons de session sur le disque...")
        time.sleep(3)
        context.close()
        print("✅ Session sauvegardée avec succès dans /tmp/chrome_session !")

if __name__ == "__main__":
    run_auth()
