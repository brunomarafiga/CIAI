"""
4_analise_bardin.py - CIAI
---------------------------
Le o relatorio_justificativas.json e executa a Análise de Conteúdo
conforme a metodologia Bardin, gerando o bardin_analysis.json.

Uso:
    python 4_analise_bardin.py
"""

import sys
import json
from collections import defaultdict
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("ERRO: 'pandas' nao encontrado. Instale com: pip install pandas")
    sys.exit(1)

import config


def identify_categories(text):
    """Retorna as categorias Bardin e as tags encontradas em um texto."""
    text_lower = text.lower()
    cats = set()
    tags = set()
    for cat, kws in config.BARDIN_CATEGORIES.items():
        for kw in kws:
            if kw in text_lower:
                cats.add(cat)
                tags.add(f"#{kw}")
    return cats, list(tags)


def analyze():
    if not config.OUTPUT_JUSTIFICATIVAS_JSON.exists():
        print("[ERRO] relatorio_justificativas.json nao encontrado.")
        print("       Execute primeiro: python 3_extrair_dados.py")
        return

    df_just = pd.read_json(config.OUTPUT_JUSTIFICATIVAS_JSON)
    print(f"\n[Bardin] {len(df_just)} justificativas carregadas.")
    print("[Bardin] Iniciando categorizacao...\n")

    bardin_res = defaultdict(list)

    for _, row in df_just.iterrows():
        just = str(row.get('Justificativa', ''))
        ind = row.get('Indicador', '?')
        course = row.get('Curso', 'N/I')

        if len(just) < 10:
            continue

        cats, tags = identify_categories(just)

        entry = {
            "indicador": ind,
            "curso": course,
            "justificativa": just,
            "tags": tags
        }

        if cats:
            for c in cats:
                bardin_res[c].append(entry)
        else:
            bardin_res["Sem Categoria"].append(entry)

    bardin_output = [
        {
            "categoria": cat,
            "total": len(entries),
            "entradas": entries
        }
        for cat, entries in bardin_res.items()
    ]

    with open(config.OUTPUT_BARDIN_JSON, "w", encoding="utf-8") as f:
        json.dump(bardin_output, f, ensure_ascii=False, indent=2)

    print(f"[Bardin] Analise salva em: {config.OUTPUT_BARDIN_JSON}")
    total_cats = sum(v['total'] for v in bardin_output)
    for cat_entry in bardin_output:
        print(f"  - {cat_entry['categoria']}: {cat_entry['total']} entradas")
    print(f"\n[OK] Total categorizado: {total_cats} entradas.")


if __name__ == "__main__":
    analyze()
