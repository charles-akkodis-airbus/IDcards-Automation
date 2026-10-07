from modules.drive_collector import fetch_drive_files
from modules.gemini_web_analyzer import analyze_files_via_web

def main():
    print("[1/2] Fetching and unzipping files from Google Drive...")
    extract_path = fetch_drive_files()

    if not extract_path:
        print("No extracted folder to process.")
        return

    print("\n[2/2] Uploading files and generating ID Card via Gemini Web...")
    report = analyze_files_via_web(extract_path)

    print("\n================ FINAL ID CARD REPORT ================\n")
    print(report)

if __name__ == "__main__":
    main()