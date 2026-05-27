"""
config.py - Configurações Compartilhadas (CIAI)
------------------------------------------------
Importado por todos os scripts de processamento.
NÃO execute este arquivo diretamente.
"""

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

# ---- Caminhos de entrada e saída ----
INPUT_DIR = Path(os.getenv("INPUT_DIR", BASE_DIR))
OUTPUT_MAP_JSON = BASE_DIR / "rename_mapping.json"
OUTPUT_RELATORIO_JSON = BASE_DIR / "relatorio.json"
OUTPUT_BARDIN_JSON = BASE_DIR / "bardin_analysis.json"
OCR_CACHE_DIR = BASE_DIR / "ocr_cache"

# ---- OCR ----
OCR_LANGUAGE = os.getenv("OCR_LANG", "pt")

# ---- Workers ----
default_workers = min(os.cpu_count() or 4, 8)
MAX_WORKERS = int(os.getenv("MAX_WORKERS", default_workers))

# ---- Padrões de Ano e Modalidade ----
YEAR_PATTERN = re.compile(r"(20\d{2})")
MODALITY_PATTERNS = {
    "Licenciatura": re.compile(r"Licenciatura|\bLic\.?\b", re.IGNORECASE),
    "Bacharelado": re.compile(r"Bacharelado|\bBach\.?\b|\bBel\.?\b", re.IGNORECASE),
    "Tecnológico": re.compile(r"Tecnológico|Tecnologia|Tecnólogo", re.IGNORECASE)
}

# ---- Mapeamento de Campus -> Cidade ----
# Regra: campus sem nome de cidade é de Curitiba.
CAMPUS_CONFIG = [
    {"name": "Campus Batel",               "pattern": re.compile(r"Batel", re.IGNORECASE),                                                                           "city": "Curitiba"},
    {"name": "Campus Centro Politécnico",  "pattern": re.compile(r"Centro\s+Politécnico|Centro\s+Polit[eé]cnico|Centro\s+Politecnico", re.IGNORECASE),               "city": "Curitiba"},
    {"name": "Campus Jandaia Do Sul",      "pattern": re.compile(r"Jandaia", re.IGNORECASE),                                                                          "city": "Jandaia do Sul"},
    {"name": "Campus Jardim Botânico",     "pattern": re.compile(r"Jardim\s+Bot[âa]nico", re.IGNORECASE),                                                            "city": "Curitiba"},
    {"name": "Campus Juvevê",              "pattern": re.compile(r"Juvev[êe]", re.IGNORECASE),                                                                        "city": "Curitiba"},
    {"name": "Campus Litoral (matinhos)",  "pattern": re.compile(r"Litoral|Matinhos", re.IGNORECASE),                                                                 "city": "Matinhos"},
    {"name": "Campus Pontal Do Sul",       "pattern": re.compile(r"Pontal|Mirassol", re.IGNORECASE),                                                                  "city": "Pontal do Paraná"},
    {"name": "Campus Reitoria",            "pattern": re.compile(r"Reitoria", re.IGNORECASE),                                                                         "city": "Curitiba"},
    {"name": "Campus Toledo",              "pattern": re.compile(r"Toledo", re.IGNORECASE),                                                                           "city": "Toledo"},
    {"name": "Hospital das Clínicas",      "pattern": re.compile(r"hospital\s+das\s+cl[íi]nicas|hospital\s+de\s+cl[íi]nicas|HC\-UFPR|Padre\s+Camargo|Alto\s+da\s+Gl[oó]ria", re.IGNORECASE), "city": "Curitiba"},
]

# ---- Categorias Bardin ----
BARDIN_CATEGORIES = {
    "1. Formalização da Inovação e Diferenciação": [
        "inovação", "inovaçao", "inovacao", "metodologia", "teoriaprática", "teoriapratica",
        "pedagógico", "pedagogico", "tecnologia", "teoria", "prática", "pratica"
    ],
    "2. Gestão, Ciclos de Feedback e Dados": [
        "feedback", "autoavaliação", "autoavaliacao", "dados", "documentação", "documentacao",
        "indicadores", "acompanhamento", "egresso", "ppc", "planejamentoausente", "nadanegativoinformado"
    ],
    "3. Adequação e Qualidade da Infraestrutura/Recursos": [
        "infraestrutura", "acessibilidade", "biblioteca", "laboratório", "laboratorio",
        "vagas", "equipamentos"
    ]
}
