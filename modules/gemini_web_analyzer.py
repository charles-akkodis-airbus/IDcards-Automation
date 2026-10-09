import os
import time
from playwright.sync_api import sync_playwright
import config

def analyze_files_via_web(extract_dir: str) -> str:
    """
    Scans extracted files, uploads them directly to Gemini Web UI,
    triggers generation, and extracts the final report.
    """
    file_paths = []
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(('.json', '.py', '.txt', '.pdf', '.csv', '.md')):
                file_paths.append(os.path.join(root, file))

    if not file_paths:
        print("No valid files found in extraction directory to analyze.")
        return ""

    print(f"Identified {len(file_paths)} file(s) for upload:")
    for path in file_paths:
        print(f"  └─ {os.path.basename(path)}")

    prompt_instruction = "Generate the complete Model Analysis ID Card using the uploaded files."

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            channel="chrome",  # <--- Utilise le Chrome installé sur la machine
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        page = context.new_page()

        print(f"Navigating to Gemini Web interface: {config.GEMINI_WEB_URL}")
        page.goto(config.GEMINI_WEB_URL)

        input_selector = "div[contenteditable='true'], textarea, div[role='textbox']"
        page.wait_for_selector(input_selector, timeout=20000)

        file_input_selector = "input[type='file']"
        page.wait_for_selector(file_input_selector, state="attached", timeout=10000)
        
        print("Uploading files to Gemini Web interface...")
        page.set_input_files(file_input_selector, file_paths)
        time.sleep(5)

        print("Entering analysis prompt instruction...")
        prompt_box = page.locator(input_selector).first
        prompt_box.click()
        prompt_box.fill(prompt_instruction)
        time.sleep(1)

        print("Submitting request to Gemini...")
        page.keyboard.press("Enter")

        print("Generating report (waiting for text stabilization)...")
        time.sleep(5)

        prev_text = ""
        stable_counter = 0

        for _ in range(60):
            time.sleep(2)
            responses = page.locator("message-content, .model-response-text, .response-container-content")
            
            if responses.count() > 0:
                current_text = responses.last.inner_text()
                if current_text and current_text == prev_text:
                    stable_counter += 1
                    if stable_counter >= 3:
                        break
                else:
                    stable_counter = 0
                    prev_text = current_text

        final_report = prev_text if prev_text else "Failed to extract generated response."
        context.close()
        return final_report