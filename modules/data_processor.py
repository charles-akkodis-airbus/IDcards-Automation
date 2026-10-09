import os
import json
from pptx import Presentation
from docx import Document
import openpyxl

def extract_text_from_pptx(filepath: str) -> str:
    """Extrait le texte de toutes les diapositives d'un fichier PowerPoint."""
    text_content = []
    try:
        prs = Presentation(filepath)
        for i, slide in enumerate(prs.slides):
            slide_text = [shape.text for shape in slide.shapes if hasattr(shape, "text")]
            if slide_text:
                text_content.append(f"--- Diapositive {i + 1} ---\n" + "\n".join(slide_text))
    except Exception as e:
        return f"[Erreur d'extraction PPTX : {e}]"
    return "\n\n".join(text_content)

def extract_text_from_docx(filepath: str) -> str:
    """Extrait le texte brut d'un fichier Word."""
    try:
        doc = Document(filepath)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"[Erreur d'extraction DOCX : {e}]"

def extract_text_from_xlsx(filepath: str) -> str:
    """Extrait le texte brut de la première feuille de calcul Excel."""
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
        sheet = wb.active
        rows = []
        for row in sheet.iter_rows(values_only=True):
            # Filtre les cellules vides et convertit en string
            row_data = [str(cell) for cell in row if cell is not None]
            if row_data:
                rows.append(" | ".join(row_data))
        return "\n".join(rows)
    except Exception as e:
        return f"[Erreur d'extraction XLSX : {e}]"

def build_master_context(download_dir: str, output_filepath: str):
    """
    Parcourt les fichiers téléchargés, extrait le texte selon le format,
    et génère un fichier JSON unique structuré pour Gemini.
    """
    master_data = {
        "metadata": {
            "source_folder": download_dir,
            "instruction": "Analyse les documents suivants extraits de l'alerte ATA pour générer une ID Card structurée."
        },
        "documents": []
    }

    for root, _, files in os.walk(download_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()
            
            doc_entry = {
                "file_name": filename,
                "file_type": ext.strip('.'),
                "content": ""
            }

            print(f" -> Extraction du contenu : {filename}")

            if ext == '.pptx':
                doc_entry["content"] = extract_text_from_pptx(filepath)
            elif ext == '.docx':
                doc_entry["content"] = extract_text_from_docx(filepath)
            elif ext == '.xlsx':
                doc_entry["content"] = extract_text_from_xlsx(filepath)
            elif ext in ['.txt', '.md', '.csv', '.json', '.py']:
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        doc_entry["content"] = f.read()
                except Exception as e:
                    doc_entry["content"] = f"[Erreur de lecture texte : {e}]"
            else:
                doc_entry["content"] = f"[Format binaire non supporté : {ext}]"

            master_data["documents"].append(doc_entry)

    # Sauvegarde du JSON
    with open(output_filepath, 'w', encoding='utf-8') as json_file:
        json.dump(master_data, json_file, ensure_ascii=False, indent=2)
    
    print(f"\n[SUCCÈS] Contexte global généré avec succès : {output_filepath}")