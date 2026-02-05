import re
import os
from pathlib import Path
import pandas as pd
import shutil
from pypdf import PdfReader
import concurrent.futures
from tqdm import tqdm

# --- CONFIGURAÇÃO ---
INPUT_DIR = Path(__file__).parent
OUTPUT_CSV = 'relatorio_justificativas.csv'
DEBUG_DIR = INPUT_DIR / 'debug_justificativas'

# Regex Patterns
# Blocks are split by indicator number.
# Capturing text after "Justificativa para conceito X:"
REGEX_JUSTIFICATIVA = re.compile(
    r"Justificativa para conceito.*?:(.*?)(?=\Z)",
    re.IGNORECASE | re.DOTALL
)

# Header info patterns (simplified from original to ensure matching)
# We need distinct patterns because we want to key by MEC ID
CODIGO_MEC_PATTERN = re.compile(r"Código\s+(?:e-MEC\s+)?do\s+Curso[:\s]+(\d{6,8})", re.IGNORECASE)
CODIGO_MEC_HEADER_PATTERN = re.compile(r"Código\s+MEC[:\s]+(\d{6,8})", re.IGNORECASE)
NOME_CURSO_HEADER_PATTERN = re.compile(
    r"Curso\(s\)\s*/\s*Habilitação\(ões\)\s+sendo\s+avaliado\(s\)[:\s]+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç\s-]+?)\s*(?:Informações|$)",
    re.IGNORECASE
)
NOME_CURSO_PATTERN = re.compile(
    r"Curso\(s\)\s*/\s*Habilitação\(ões\)[^:]*?:\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç\s-]+?)\s*;\s*Grau",
    re.IGNORECASE
)

MAX_WORKERS = os.cpu_count()

def extract_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
            text += "\n"
        return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def formatar_inteiro(valor):
    if not valor: return None
    try: return int(str(valor).strip())
    except: return valor

def extract_metadata(text):
    data = {'Curso': None, 'Id_MEC': None}
    
    # Curso
    m = NOME_CURSO_HEADER_PATTERN.search(text) or NOME_CURSO_PATTERN.search(text)
    if m: data['Curso'] = m.group(1).strip()
    
    # Id_MEC
    # Strategy 1: Explicit labels
    m = CODIGO_MEC_HEADER_PATTERN.search(text) or CODIGO_MEC_PATTERN.search(text)
    if m: 
        data['Id_MEC'] = str(formatar_inteiro(m.group(1)))
    else:
        # Strategy 2: Fallback for table layout where values are detached
        # Look for 7-digit number which is likely the Course ID (Protocolo is 9, Avaliacao is 6 usually)
        # We search specifically in the first 1000 chars roughly to avoid false positives later in text
        candidates = re.findall(r'\b(\d{7})\b', text[:2000])
        if candidates:
            # We pick the first 7-digit number found.
            # Usually Protocolo (9 digits) and Avaliação (6 digits) won't match.
            data['Id_MEC'] = str(candidates[0])
            print(f"DEBUG: Used fallback ID extraction: {data['Id_MEC']}")
    
    return data

def extract_justifications(text):
    justifications = {}
    
    # Split text into blocks starting with "1.1.", "1.2.", etc.
    # Using specific split to avoid false positives
    # The pattern (?=^\s*\d+\.\d+\.) looks ahead for "1.1." at start of line
    # We first ensure newlines are clean to regex against
    clean_text = re.sub(r'\r\n', '\n', text)
    
    # We want to identify the indicator.
    # Strategy: Find all indices of "^ X.Y. " and slice the text.
    
    # Matches "1.1." or "1.1" followed by space? standard is "1.1. Name"
    # Dump showing: "1.1. Políticas ... 5"
    
    # Let's split by the indicator number pattern
    # Use capturing group to keep the delimiter (the indicator number)
    parts = re.split(r'(^\s*\d+\.\d+\.)', clean_text, flags=re.MULTILINE)
    
    # parts[0] is preamble
    # parts[1] is indicator (e.g. "1.1.")
    # parts[2] is content
    # parts[3] is next indicator...
    
    for i in range(1, len(parts), 2):
        indicator_num = parts[i].strip().strip('.') # Remove trailing dot "1.1." -> "1.1"
        try:
            content = parts[i+1]
        except IndexError:
            content = ""
            
        # Extract justification from content
        m = REGEX_JUSTIFICATIVA.search(content)
        if m:
            just_text = m.group(1).strip()
            # Clean up: remove "Justificativa para conceito X:" artifacts if regex leaked (it shouldn't)
            # Remove common footer text that might have been caught if split failed
            # But the split logic separates blocks, so footer is usually at end of page.
            # Page breaks like "--- Page X ---" might be in the middle of text.
            just_text = re.sub(r'--- Page \d+ ---', '', just_text)
            just_text = re.sub(r'\s+', ' ', just_text).strip()
            
            justifications[indicator_num] = just_text
            
    return justifications

def process_pdf(pdf_path):
    print(f"Processing: {pdf_path.name}")
    text = extract_text(pdf_path)
    if not text:
        return None
        
    metadata = extract_metadata(text)
    
    # Fallback for Curso name if regex failed
    if not metadata['Curso']:
        # Use filename, removing "2025 - " prefix if present to be cleaner
        clean_name = pdf_path.stem
        clean_name = re.sub(r'^\d{4}\s*-\s*', '', clean_name)
        metadata['Curso'] = clean_name
        
    justifs = extract_justifications(text)
    
    # Merge
    row = metadata
    row.update(justifs)
    return row

def main():
    pdf_files = list(INPUT_DIR.glob('*.pdf'))
    print(f"Found {len(pdf_files)} PDFs.")
    
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_pdf, p): p for p in pdf_files}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            res = future.result()
            if res:
                results.append(res)
                
    if not results:
        print("No results extracted.")
        return

    df = pd.DataFrame(results)
    
    # Ensure columns exist and order them
    # Indicators 1.1 to 1.24, 2.1 to 2.16, 3.1 to 3.17
    indicators = []
    for i in range(1, 25): indicators.append(f"1.{i}")
    for i in range(1, 17): indicators.append(f"2.{i}")
    for i in range(1, 18): indicators.append(f"3.{i}")
    
    # Base columns
    cols = ['Curso', 'Id_MEC'] + indicators
    
    # Add any missing cols to df
    for c in cols:
        if c not in df.columns:
            df[c] = None
            
    # Select only these cols (ignore others like 4.1 etc if captured)
    df = df[cols]
    
    # Ensure Id_MEC is string and has no .0
    df['Id_MEC'] = df['Id_MEC'].astype(str)
    df['Id_MEC'] = df['Id_MEC'].str.replace(r'\.0$', '', regex=True)
    df['Id_MEC'] = df['Id_MEC'].replace('nan', '')
    df['Id_MEC'] = df['Id_MEC'].replace('None', '')
    
    # Sort by Id_MEC
    df.sort_values('Id_MEC', inplace=True)
    
    print(f"Saving to {OUTPUT_CSV}...")
    # Use semi-colon separator and utf-8-sig
    df.to_csv(OUTPUT_CSV,  sep=';', index=False, encoding='utf-8-sig', quoting=1) # quote all to handle text with semi-colons

if __name__ == "__main__":
    main()
