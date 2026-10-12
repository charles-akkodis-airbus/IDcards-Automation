import os
import time
from playwright.sync_api import sync_playwright
import config

def analyze_files_via_web(extract_dir: str = config.EXTRACT_DIR):
    """Téléverse les fichiers extraits dans Gemini Web et récupère l'analyse."""
    valid_extensions = ('.json', '.py', '.txt', '.pdf', '.csv', '.md')
    files_to_upload = []

    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(valid_extensions):
                files_to_upload.append(os.path.join(root, f))

    if not files_to_upload:
        print("Aucun fichier valide trouvé dans le dossier d'extraction.")
        return

    print(f"Fichiers identifiés pour envoi : {len(files_to_upload)}")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            channel="chrome",
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()
        print(f"Navigation vers Gemini : {config.GEMINI_WEB_URL}")
        page.goto(config.GEMINI_WEB_URL)

        # Attente du champ de saisie
        prompt_box = page.wait_for_selector("div[contenteditable='true'], textarea, div[role='textbox']", timeout=30000)
        
        # Téléversement des fichiers
        file_input = page.locator("input[type='file']").first
        file_input.set_input_files(files_to_upload)
        time.sleep(2)

        # Envoi de la consigne
        instruction = "Génère la fiche d'analyse complète (ID Card) à partir des fichiers fournis."
        prompt_box.fill(instruction)
        page.keyboard.press("Enter")

        print("Demande envoyée. Attente de la réponse...")
        time.sleep(10)

        # Récupération du résultat
        response_element = page.locator(".message-content, .model-response-text, .response-container-content").last
        if response_element.is_visible():
            print("\n=== RÉPONSE GEMINI ===")
            print(response_element.inner_text())
        else:
            print("Impossible de récupérer la réponse automatiquement.")

        browser.close()