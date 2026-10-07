import sys
from modules.drive_collector import fetch_drive_files, normalize_fleet, normalize_ata
from modules.gemini_web_analyzer import analyze_files_via_web

def prompt_user_inputs() -> dict:
    print("==================================================")
    print("      AIRCRAFT MODEL ANALYSIS PIPELINE            ")
    print("==================================================\n")

    # 1. Fleet Input
    raw_fleet = input("Enter Fleet (e.g. A320, A350): ").strip()
    fleet = normalize_fleet(raw_fleet)

    # 2. ATA Input
    raw_ata = input("Enter ATA Chapter (e.g. 21, ATA21): ").strip()
    ata = normalize_ata(raw_ata)

    # 3. Alert Title Input
    alert_title = input("Enter Alert Title / Description: ").strip()

    print("\n--- RESOLVED PARAMETERS ---")
    print(f"  • Fleet Family : {fleet}")
    print(f"  • Workspace    : 00_Model Workspace")
    print(f"  • ATA Chapter  : {ata}")
    print(f"  • Target Alert : {alert_title}")
    print("---------------------------\n")

    return {
        "fleet": fleet,
        "workspace": "00_Model Workspace",
        "ata": ata,
        "alert_title": alert_title
    }

def main():
    # Gather interactive parameters
    params = prompt_user_inputs()

    print("[1/2] Searching, downloading, and unzipping Drive files...")
    extract_path = fetch_drive_files(params)

    if not extract_path:
        print("No folder matched the search criteria. Aborting pipeline.")
        sys.exit(1)

    print("\n[2/2] Uploading files and generating ID Card via Gemini Web...")
    report = analyze_files_via_web(extract_path)

    print("\n================ FINAL ID CARD REPORT ================\n")
    print(report)

if __name__ == "__main__":
    main()