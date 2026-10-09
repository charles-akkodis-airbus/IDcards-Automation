import sys
import os
from modules.drive_collector import fetch_drive_files, normalize_fleet, normalize_ata
from modules.data_processor import build_master_context

def prompt_user_inputs() -> dict:
    print("==================================================")
    print("      AIRCRAFT MODEL DATA EXTRACTION PIPELINE     ")
    print("==================================================\n")

    raw_fleet = input("Enter Fleet (e.g. A320, A350): ").strip()
    fleet = normalize_fleet(raw_fleet)

    raw_ata = input("Enter ATA Chapter (e.g. 21, ATA21): ").strip()
    ata = normalize_ata(raw_ata)

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
    params = prompt_user_inputs()

    print("[1/2] Recherche et téléchargement récursif des fichiers Drive...")
    download_path = fetch_drive_files(params)

    if not download_path or not os.path.exists(download_path):
        print("Aucun dossier ne correspond aux critères. Interruption du programme.")
        sys.exit(1)

    print("\n================ EXTRACTION TERMINÉE ================")
    print(f"Dossier de destination : {download_path}\n")

    print("[2/2] Génération du fichier de contexte JSON pour Gemini...")
    output_json = os.path.join(download_path, "master_context_gemini.json")
    build_master_context(download_path, output_json)

    print("\n================ PRÊT POUR L'ANALYSE ================")
    print(f"1. Ouvre ton Gem sur l'interface Gemini.")
    print(f"2. Glisse-dépose le fichier : {output_json}")

if __name__ == "__main__":
    main()