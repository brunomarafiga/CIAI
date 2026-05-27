"""
1_gerar_mapa_renomeacao.py - CIAI
---------------------------------
APENAS gera o arquivo rename_mapping.json com o mapeamento de
nome original -> nome novo. NÃO renomeia nenhum arquivo.

Execute depois: 2_aplicar_renomeacao.py (apenas quando quiser renomear).

Uso:
    python 1_gerar_mapa_renomeacao.py
"""

import os
import re
import sys
import json
import hashlib
from pathlib import Path

import config

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# Cidades a remover do nome do curso (para limpar resíduos de corridas anteriores)
_CITY_STRIP = re.compile(
    r'\b(?:Curitiba|Jandaia\s+do\s+Sul|Jandaia|Matinhos|Pontal\s+do\s+Paraná|Pontal|Toledo)\b',
    re.IGNORECASE
)

def clean_course_name(filename, year, modality):
    name = os.path.splitext(filename)[0]

    # Remove ano
    if year and year != "UNKNOWN_YEAR":
        name = name.replace(year, "")

    # Remove modalidade
    for pattern in config.MODALITY_PATTERNS.values():
        name = pattern.sub('', name)

    # Remove padrões de campus
    for c_conf in config.CAMPUS_CONFIG:
        name = c_conf["pattern"].sub('', name)

    # Remove nomes de cidades que ficaram acumulados em corridas anteriores
    name = _CITY_STRIP.sub('', name)

    # Remove termos genéricos
    ignore_patterns = [
        r'\bRelatório\b', r'\bRelatorio\b', r'\bAvaliação\b', r'\bin loco\b',
        r'\bMEC\b', r'\bINEP\b', r'\be-MEC\b', r'\bCurso\b', r'\bde\b', r'\bdo\b', r'\bda\b'
    ]
    for pat in ignore_patterns:
        name = re.sub(pat, ' ', name, flags=re.IGNORECASE)

    name = re.sub(r'\(\s*\)', '', name)        # remove "()" vazios
    name = re.sub(r'\s*-+\s*', ' ', name)      # normaliza hifens
    name = re.sub(r'\s+', ' ', name).strip()   # normaliza espaços

    corrections = {
        "relatorioartes": "Artes Visuais",
        "ed. física": "Educação Física",
        "ciência computação": "Ciência da Computação"
    }
    return corrections.get(name.lower(), name)


# ==============================================================================
# GERAÇÃO DO MAPA
# ==============================================================================

def generate_mapping(directory):
    print(f"\n[Renamer] Gerando mapa de renomeacao para: {directory}")
    results = []
    seen_hashes = {}
    seen_names = {}

    files = list(Path(directory).glob("*.pdf"))
    print(f"[Renamer] Encontrados {len(files)} arquivos PDF...")

    for filepath in files:
        filename = filepath.name

        year_match = config.YEAR_PATTERN.search(filename)
        year = year_match.group(1) if year_match else "202X"

        modality = "N/A"
        for mod, pat in config.MODALITY_PATTERNS.items():
            if pat.search(filename):
                modality = mod
                break

        city = "Curitiba"
        for c_conf in config.CAMPUS_CONFIG:
            if c_conf["pattern"].search(filename):
                city = c_conf["city"]
                break

        course_name = clean_course_name(filename, year, modality)

        mod_str = f" ({modality})" if modality != "N/A" else ""
        new_name = f"{year} - {course_name}{mod_str} - {city}.pdf"

        fhash = get_file_hash(filepath)
        is_dup = fhash in seen_hashes
        dup_of = seen_hashes.get(fhash, "")
        if not is_dup:
            seen_hashes[fhash] = filepath

        if new_name in seen_names and not is_dup:
            base, ext = os.path.splitext(new_name)
            counter = 2
            while f"{base} ({counter}){ext}" in seen_names:
                counter += 1
            new_name = f"{base} ({counter}){ext}"

        seen_names[new_name] = filepath

        results.append({
            "Original Path": str(filepath),
            "Original Name": filename,
            "New Name": new_name,
            "Duplicate Status": "Duplicate" if is_dup else "Original",
            "Duplicate Of": str(dup_of),
            "Hash": fhash
        })

    with open(config.OUTPUT_MAP_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"[Renamer] Mapa salvo em: {config.OUTPUT_MAP_JSON}")
    print(f"[Renamer] Total: {len(results)} arquivos mapeados.")
    print("\nRevisione o arquivo rename_mapping.json antes de executar 2_aplicar_renomeacao.py")


if __name__ == "__main__":
    generate_mapping(config.INPUT_DIR)
