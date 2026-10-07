import os
import re
import time
import zipfile
import urllib.parse
from playwright.sync_api import sync_playwright
import config

def extract_folder_id(drive_url: str) -> str | None:
    """Extracts the folder ID from a standard Google Drive URL."""
    match = re.search(r"folders/([a-zA-Z0-9_-]+)", drive_url)
    return match.group(1) if match else None

def build_drive_search_url(root_url: str, criteres: dict) -> str:
    """Constructs a scoped Google Drive search URL using filters."""
    folder_id = extract_folder_id(root_url)
    query_parts = ["type:folder"]
    
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")

    for value in criteres.values():
        if value:
            query_parts.append(f'"{value}"')

    encoded_query = urllib.parse.quote(" ".join(query_parts))
    return f"https://drive.google.com/drive/search?q={encoded_query}"

def fetch_drive_files() -> str:
    """
    Navigates to the targeted Drive folder via search URL, selects all files,
    downloads the generated ZIP archive, and extracts it to /tmp/extracted.
    """
    search_url = build_drive_search_url(config.DRIVE_ROOT_URL, config.DRIVE_FILTRES)
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(config.EXTRACT_DIR, exist_ok=True)

    print(f"Navigating to Drive search URL: {search_url}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        page = context.new_page()
        page.goto(search_url)

        print("Analyzing search results on Google Drive...")
        page.wait_for_selector("div[role='main']", timeout=15000)
        time.sleep(2)

        items = page.locator("div[role='row'], div[role='gridcell']")

        if items.count() > 0:
            print("Target folder found. Opening...")
            items.first.click()
            time.sleep(0.5)
            page.keyboard.press("Enter")
            time.sleep(3)

            print("Selecting all folder contents (Ctrl+A)...")
            page.locator("div[role='main']").click()
            page.keyboard.press("Control+a")
            time.sleep(1)

            page.locator("div[role='row'], div[role='gridcell']").first.click(button="right")
            
            print("Waiting for Google Drive ZIP generation and download...")
            with page.expect_download(timeout=180000) as download_info:
                page.get_by_text("Télécharger", exact=True).click()

            download = download_info.value
            zip_path = os.path.join(config.DOWNLOAD_DIR, download.suggested_filename)
            download.save_as(zip_path)
            print(f"ZIP archive saved to: {zip_path}")

            print("Extracting ZIP contents...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(config.EXTRACT_DIR)
            print(f"Extracted files ready in: {config.EXTRACT_DIR}")
        else:
            print("No matching folders found on Google Drive.")

        context.close()

    return config.EXTRACT_DIR