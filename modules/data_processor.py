import os

def read_extracted_data(extract_dir: str) -> str:
    combined_text = []
    
    for root, _, files in os.walk(extract_dir):
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            
            if ext == '.json':
                tag = "PARAMETERS FILE (JSON - Primary source for thresholds & configurations)"
            elif ext == '.py':
                tag = "ARCHITECTURE CODE (Python - Primary source for structure)"
            elif ext in ['.txt', '.md', '.csv']:
                tag = f"TECHNICAL DOCUMENTATION ({file})"
            else:
                continue
                
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                combined_text.append(f"=== {tag} ===\n{f.read()}\n")
                
    # Le return doit se trouver HORS de la boucle for
    return "\n".join(combined_text)