import os
import re
import csv
import hashlib

# Configuration
ROOT_DIR = r"c:/Users/bruno/OneDrive - ufpr.br/Arquivos de Coordenadoria de Indicadores E Avaliação Institucional - 1 - AVALIAÇÃO IN LOCO/2 - RELATÓRIOS/Relatórios 2022-2025"
OUTPUT_CSV = r"c:/Users/bruno/OneDrive - ufpr.br/Arquivos de Coordenadoria de Indicadores E Avaliação Institucional - 1 - AVALIAÇÃO IN LOCO/2 - RELATÓRIOS/Relatórios 2022-2025/rename_mapping.csv"

# Regex patterns
YEAR_PATTERN = re.compile(r"(202[2-5])")
MODALITY_PATTERNS = {
    "Licenciatura": re.compile(r"Licenciatura|Lic\.?|Lic", re.IGNORECASE),
    "Bacharelado": re.compile(r"Bacharelado|Bach\.?|Bel\.?|Bel", re.IGNORECASE)
}
CITY_PATTERNS = {
    "Jandaia do Sul": re.compile(r"Jandaia", re.IGNORECASE),
    "Toledo": re.compile(r"Toledo", re.IGNORECASE),
    "Pontal do Paraná": re.compile(r"Pontal", re.IGNORECASE),
    "Matinhos": re.compile(r"Matinhos", re.IGNORECASE),
    "Palotina": re.compile(r"Palotina", re.IGNORECASE),
    "Curitiba": re.compile(r"Curitiba", re.IGNORECASE) # Explicit check, otherwise default
}

IGNORE_TERMS = [
    r"Relatório", r"Relatorio", r"Relatórito", r"Avaliação", r"in loco", 
    r"MEC", r"INEP", r"e-MEC", r"IES", r"Curso", r"de", r"do", r"da", r"-"
]

# Manual corrections for specific problematic filenames
MANUAL_COURSE_CORRECTIONS = {
    "relatorioartes": "Artes Visuais",
    "relatórioexprgraf": "Expressão Gráfica",
    "relatórioibm": "Informática Biomédica",
    "relatórioinglês": "Letras Inglês",
    "relatoriovisitainlocogi": "Gestão da Informação",
    "e gestão empreendedorismo": "Gestão e Empreendedorismo",
    "publicidade e propaganda": "Publicidade e Propaganda",
    "adm publica": "Administração Pública",
    "gestao imobiliaria": "Gestão Imobiliária",
    "ed. física": "Educação Física",
    "relatóriobacharelado ed. física": "Educação Física",
    "ciência computação": "Ciência da Computação",
    "ciências biológicas": "Ciências Biológicas",
    "agroecologia": "Agroecologia",
    "geologia": "Geologia",
    "pedagogia": "Pedagogia",
    "educação campo ciências natureza": "Educação do Campo - Ciências da Natureza",
    "gestão turismo": "Gestão de Turismo",
    "secretaria": "Secretariado",
    "tni": "Tecnologia em Negócios Imobiliários",
    "quimica": "Química",
    "produção cultural": "Produção Cultural",
    "enfermagem": "Enfermagem"
}

def get_file_hash(filepath):
    """Calculates MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def clean_course_name(filename, year, modality, city):
    """Extracts and cleans course name from filename."""
    name = os.path.splitext(filename)[0]
    
    # Remove Year
    if year and year != "UNKNOWN_YEAR":
        name = name.replace(year, "")
        
    # Remove Modality terms - use word boundaries
    modality_terms = [
        r'\bLicenciatura\b', r'\bLic\.\b', r'\bLic\b',
        r'\bBacharelado\b', r'\bBach\.\b', r'\bBach\b', 
        r'\bBel\.\b', r'\bBel\b'
    ]
    for term in modality_terms:
        name = re.sub(term, '', name, flags=re.IGNORECASE)
        
    # Remove City terms - use word boundaries
    city_terms = [
        r'\bJandaia( do Sul)?\b',
        r'\bToledo\b',
        r'\bPontal( do Paraná)?\b',
        r'\bMatinhos\b',
        r'\bPalotina\b',
        r'\bCuritiba\b'
    ]
    for term in city_terms:
        name = re.sub(term, '', name, flags=re.IGNORECASE)
        
    # Remove common report-related terms - use word boundaries
    ignore_patterns = [
        r'\bRelatório\b', r'\bRelatorio\b', r'\bRelatórito\b', r'\bRelaório\b',
        r'\bAvaliação\b', r'\bin loco\b', r'\bvisita\b', r'\bvisitainloco\b',
        r'\bMEC\b', r'\bINEP\b', r'\be-MEC\b', r'\bIES\b', 
        r'\bCurso( de)?\b', r'\bde\b', r'\bdo\b', r'\bda\b', r'\bdos\b', r'\bdas\b',
        r'\baguardando\b', r'\banálise\b', r'\brecurso\b',
        r'\bParecer\b', r'\bCTAA\b', r'\bsobre\b', r'\bResultado\b',
        r'\bead\b'
    ]
    
    for pattern in ignore_patterns:
        name = re.sub(pattern, ' ', name, flags=re.IGNORECASE)
        
    # Clean up dashes and underscores at word boundaries
    name = re.sub(r'\s*-+\s*', ' ', name)
    name = re.sub(r'\s*_+\s*', ' ', name)
    
    # Remove standalone numbers in parentheses like (1)
    name = re.sub(r'\(\d+\)', '', name)
    
    # Clean up whitespace
    name = re.sub(r'\s+', ' ',name).strip()
    
    # Remove leading/trailing non-alphanumeric chars (except parentheses for internal use)
    name = re.sub(r'^[^\w\u00C0-\u00FF(]+|[^\w\u00C0-\u00FF)]+$', '', name, flags=re.UNICODE)
    
    # Apply manual corrections - use exact match
    name_normalized = name.lower().strip()
    if name_normalized in MANUAL_COURSE_CORRECTIONS:
        name = MANUAL_COURSE_CORRECTIONS[name_normalized]
    
    return name.strip()

def process_files():
    results = []
    seen_hashes = {}
    seen_names = {}  # Track duplicate new names
    
    for root, dirs, files in os.walk(ROOT_DIR):
        for file in files:
            if not file.lower().endswith(".pdf"):
                continue
                
            filepath = os.path.join(root, file)
            
            # 1. Extract Year
            year_match = YEAR_PATTERN.search(file)
            year = year_match.group(1) if year_match else None
            if not year:
                # Try parent folder
                parent_folder = os.path.basename(root)
                year_match = YEAR_PATTERN.search(parent_folder)
                year = year_match.group(1) if year_match else None
                
                # If still not found, try grandparent folder
                if not year:
                    grandparent_folder = os.path.basename(os.path.dirname(root))
                    year_match = YEAR_PATTERN.search(grandparent_folder)
                    year = year_match.group(1) if year_match else "UNKNOWN_YEAR"

            # 2. Extract Modality
            modality = "N/A"
            for mod, pattern in MODALITY_PATTERNS.items():
                if pattern.search(file):
                    modality = mod
                    break
            
            # 3. Extract City
            city = "Curitiba" # Default
            for cit, pattern in CITY_PATTERNS.items():
                if pattern.search(file):
                    city = cit
                    break
            
            # 4. Extract Course Name
            course_name = clean_course_name(file, year, modality, city)
            
            # 4.5. Fix specific modality assignments
            course_name_lower = course_name.lower()
            if "publicidade" in course_name_lower or "propaganda" in course_name_lower:
                modality = "Bacharelado"
            elif "relações públicas" in course_name_lower:
                modality = "Bacharelado"
            elif "administração pública" in course_name_lower and "ead" not in file.lower():
                modality = "Bacharelado"
            
            # 5. Construct New Name
            # Format: [Year] - [Course Name] ([Modality]) - [City].pdf
            modality_str = f" ({modality})" if modality != "N/A" else ""
            new_name = f"{year} - {course_name}{modality_str} - {city}.pdf"
            
            # 6. Duplicate Detection
            file_hash = get_file_hash(filepath)
            is_duplicate = False
            duplicate_of = ""
            
            if file_hash in seen_hashes:
                is_duplicate = True
                duplicate_of = seen_hashes[file_hash]
            else:
                seen_hashes[file_hash] = filepath
            
            # 7. Detect name conflicts (different files with same new name)
            if new_name in seen_names and not is_duplicate:
                # Name conflict! Add a suffix
                base, ext = os.path.splitext(new_name)
                counter = 2
                while f"{base} ({counter}){ext}" in seen_names:
                    counter += 1
                new_name = f"{base} ({counter}){ext}"
            
            seen_names[new_name] = filepath
                
            results.append({
                "Original Path": filepath,
                "New Name": new_name,
                "Duplicate Status": "Duplicate" if is_duplicate else "Original",
                "Duplicate Of": duplicate_of,
                "Hash": file_hash
            })

    # Write to CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as csvfile:
        fieldnames = ["Original Path", "New Name", "Duplicate Status", "Duplicate Of", "Hash"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Processing complete. Mapping saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    process_files()
