"""
extração.py
-----------
Extrai dados estruturados de relatórios de avaliação in loco (PDF) e gera:
  - relatorio_consolidado_extraido.json  (um registro por PDF)
  - relatorio_justificativas.json        (um registro por indicador)

Depende de: config.py (no mesmo diretório)

Uso:
    python extração.py
"""

import re
import sys
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import config

try:
    import pandas as pd
except ImportError:
    print("ERRO: 'pandas' não encontrado. Instale com: pip install pandas")
    sys.exit(1)

try:
    import fitz
except ImportError:
    print("ERRO: 'pymupdf' (fitz) não encontrado. Instale com: pip install pymupdf")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs): return iterable

try:
    import os
    # Suppress Paddle C++ logs before importing
    os.environ["GLOG_minloglevel"] = "2"
    os.environ["KMP_WARNINGS"] = "0"
    os.environ["PADDLE_DISABLE_WARNING"] = "1"
    
    from paddleocr import PaddleOCR
    import numpy as np
    from PIL import Image
    import io
    Image.MAX_IMAGE_PIXELS = None
    OCR_AVAILABLE = True
    
    _ocr_instance = None
    def get_ocr():
        global _ocr_instance
        if _ocr_instance is None:
            import os, sys, logging
            logging.getLogger("ppocr").setLevel(logging.ERROR)
            logging.getLogger("paddlex").setLevel(logging.ERROR)
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            with open(os.devnull, 'w') as fnull:
                sys.stdout = fnull
                sys.stderr = fnull
                try:
                    _ocr_instance = PaddleOCR(use_angle_cls=True, lang=config.OCR_LANGUAGE)
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
        return _ocr_instance
except ImportError:
    OCR_AVAILABLE = False

# ==============================================================================
# PADRÕES DE EXTRAÇÃO
# ==============================================================================

# Indicadores válidos: 1.1–1.24 | 2.1–2.16 | 3.1–3.17
INDICATOR_SPLIT = re.compile(
    r'(^\s*(?:1\.(?:[1-9]|1[0-9Oo]|2[0-4Oo])|2\.(?:[1-9]|1[0-6Oo])|3\.(?:[1-9]|1[0-7Oo]))\.)',
    re.MULTILINE
)

PATTERNS = {
    'curso': [
        re.compile(r"Curso\(s\).*?avaliado\(s\)[:\s]+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\w\s-]+?)(?:\s*Informações|$)", re.I),
        re.compile(r"Curso\(s\)[^:]*?:\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\w\s-]+?)(?:\s*;\s*Grau)", re.I),
    ],
    'mec_id': [
        re.compile(r"Código\s+(?:e-?)?MEC[:\s]+([0-9Oo]{6,8})", re.I),
        re.compile(r"(?:e-?)?MEC[:\s]+([0-9Oo]{6,8})", re.I),
        re.compile(r"Código[:\s]+([0-9Oo]{6,8})\b", re.I),
    ],
    'ano':       re.compile(r"Período\s+de\s+Visita.*?/([2Zz][0-9Oo]{3})", re.I),
    'conceitos': re.compile(r"CONCEITO\s+FINAL\s+CONT[ÍI]NUO.*?([\d,.]+)\s+([\d,.]+)", re.I | re.DOTALL),
    'dimensao':  re.compile(r"Dimensão\s+(\d):\s*([1-5][\.,]\d{1,2}|[1-5])", re.I),
    'ind_justif': re.compile(r"Justificativa para conceito.*?:(.*?)(?=\Z)", re.I | re.DOTALL),
    'ind_nota':   re.compile(r"(?:Conceito|Nota).*?[:\s]+([1-5]|NSA|Não se aplica|N/A)", re.I),
    'endereco': [
        re.compile(r"Endere[çc]o\s+da\s+(?:TES|IES|Instituição)[:\s]+(.*?)(?=CEP|Curso\(s\)|\n\n|\Z)", re.I | re.DOTALL),
        re.compile(r"Endere[çc]o\s+de\s+funcionamento\s+do\s+curso[:\s]+(.*?)(?=\Z|\n\n)", re.I | re.DOTALL),
        re.compile(r"Endere[çc]o\s+de\s+funcionamento[:\s]+(.*?)(?=\Z|\n\n)", re.I | re.DOTALL),
    ],
}


# ==============================================================================
# LIMPEZA E NORMALIZAÇÃO DE TEXTO
# ==============================================================================

def normalize_text(text: str) -> str:
    # Junta hifenizações de quebra de linha: "avalia-\nção" → "avaliação"
    text = re.sub(r'-\s*\n\s*', '', text)
    # Quebras múltiplas viram parágrafo duplo (preserva estrutura semântica)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Múltiplos espaços → um espaço
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()

def clean_mec_id(raw: str) -> str:
    if not raw:
        return "N/I"
    cleaned = re.sub(r'[Oo]', '0', raw)
    cleaned = re.sub(r'\D', '', cleaned)
    if not cleaned:
        return "N/I"
    return cleaned.zfill(8)

NOTAS_VALIDAS = {"1", "2", "3", "4", "5"}

def normalize_nota(raw: str | None) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if raw in NOTAS_VALIDAS:
        return raw
    if re.match(r'^[Nn]', raw):  # NSA, Não se aplica, N/A, NSA/NI etc.
        return "NSA"
    return raw

def clean_justificativa(text: str, max_chars: int = 2000) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "…"
    return text or "N/I"


# ==============================================================================
# EXTRAÇÃO DE TEXTO DO PDF
# ==============================================================================

def extract_text(pdf_path: Path, use_ocr: bool = False) -> str:
    text = ""
    try:
        if use_ocr and OCR_AVAILABLE:
            ocr = get_ocr()
            doc = fitz.open(pdf_path)
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                result = ocr.ocr(img_array, cls=True)
                if result and result[0]:
                    for line in result[0]:
                        text += line[1][0] + "\n"
        else:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += (page.get_text("text", sort=True) or "") + "\n"
    except Exception as e:
        print(f"  [Erro] {pdf_path.name}: {e}")
    return text


# ==============================================================================
# IDENTIFICAÇÃO DE CAMPUS E CIDADE
# ==============================================================================

def detectar_campus(text: str, pdf_name: str) -> dict | None:
    """Retorna o item de CAMPUS_CONFIG correspondente, ou None."""

    # 1. Endereço da IES/TES
    for p in PATTERNS['endereco']:
        m = p.search(text)
        if m:
            trecho = m.group(1).replace('\n', ' ')
            matched = [c for c in config.CAMPUS_CONFIG if c["pattern"].search(trecho)]
            if matched:
                hc = [c for c in matched if "clinicas" in c["name"].lower()]
                return hc[0] if hc else matched[0]

    # 2. Primeiros 2000 caracteres
    trecho = text[:2000]
    matched = [c for c in config.CAMPUS_CONFIG if c["pattern"].search(trecho)]
    if matched:
        hc = [c for c in matched if "clinicas" in c["name"].lower()]
        return hc[0] if hc else matched[0]

    # 3. Nome do arquivo
    matched = [c for c in config.CAMPUS_CONFIG if c["pattern"].search(pdf_name)]
    return matched[0] if matched else None


# ==============================================================================
# PARSING DO CONTEÚDO
# ==============================================================================

def parse(text: str, pdf_name: str) -> tuple[dict, list[dict]]:
    """
    Retorna (metadados_do_pdf, lista_de_justificativas).
    """
    meta = {
        'ID_DOCUMENTO': pdf_name,
        'Curso': None, 'Id_MEC': None,
        'Ano_avaliacao': None, 'Modalidade': None,
        'Cidade': None, 'Campus': None,
    }

    # ---- Curso ----
    for p in PATTERNS['curso']:
        m = p.search(text)
        if m and len(m.group(1)) < 100:
            meta['Curso'] = m.group(1).strip()
            break
    if not meta['Curso']:
        base = re.sub(r'202[2-5]\s*-\s*', '', pdf_name)
        base = re.sub(r'\s*\([^)]+\).*', '', base)
        base = re.sub(r'\s*-\s*.*', '', base)
        meta['Curso'] = base.replace('.pdf', '').strip().upper()

    # ---- Id MEC ----
    for p in PATTERNS['mec_id']:
        m = p.search(text)
        if m:
            meta['Id_MEC'] = clean_mec_id(m.group(1))
            break

    # ---- Ano ----
    m = PATTERNS['ano'].search(text)
    if m:
        meta['Ano_avaliacao'] = m.group(1).upper().replace('O', '0').replace('Z', '2')
    else:
        y = config.YEAR_PATTERN.search(pdf_name)
        if y:
            meta['Ano_avaliacao'] = y.group(1)

    # ---- Modalidade: tenta 4 fontes em ordem de prioridade ----
    found_mod = None
    m_mod = re.search(r"\b(?:Modalidade|Grau)\s*:\s*([^\n]{2,30})", text, re.I)
    for candidato in [
        m_mod.group(1) if m_mod else "",
        meta['Curso'] or "",
        pdf_name,
        text,          # texto completo como fallback final
    ]:
        for mod, pat in config.MODALITY_PATTERNS.items():
            if pat.search(candidato):
                found_mod = mod
                break
        if found_mod:
            break
    meta['Modalidade'] = found_mod or "N/A"

    # ---- Campus / Cidade ----
    campus = detectar_campus(text, pdf_name)
    if campus:
        meta['Campus'] = campus['name']
        meta['Cidade'] = campus['city']
    else:
        meta['Campus'] = "N/I"
        meta['Cidade'] = "N/I"

    # Substituir None restantes
    for k, v in meta.items():
        if v is None:
            if k == 'Modalidade':
                meta[k] = "N/A"
            else:
                meta[k] = "N/I"

    # ---- Notas de Dimensão ----
    for dim, val in PATTERNS['dimensao'].findall(text):
        meta[f'Dimensao_{dim}'] = float(val.replace(',', '.'))

    # ---- Conceito Final ----
    m_block = re.search(r"CONCEITO\s+FINAL\s+CONT[ÍI]NUO(.{0,150})", text, re.I | re.DOTALL)
    if m_block:
        block = m_block.group(1)
        # Extrair números (ex: 4,69 ou 5 ou 4.46)
        nums = re.findall(r'\b\d(?:[.,]\d+)?\b', block)
        valid_nums = []
        for n in nums:
            try:
                v = float(n.replace(',', '.'))
                if 1 <= v <= 5:
                    valid_nums.append(v)
            except ValueError:
                pass
                
        if len(valid_nums) >= 2:
            meta['CONCEITO_FINAL_CONTINUO'] = valid_nums[0]
            meta['CONCEITO_FINAL_FAIXA'] = int(valid_nums[1]) if valid_nums[1].is_integer() else valid_nums[1]
        elif len(valid_nums) == 1:
            val = valid_nums[0]
            if val.is_integer() and val >= 1:
                meta['CONCEITO_FINAL_FAIXA'] = int(val)
            else:
                meta['CONCEITO_FINAL_CONTINUO'] = val

    # ---- Justificativas por indicador ----
    justificativas = []
    parts = INDICATOR_SPLIT.split(text)

    primeiro_indicador = True
    for i in range(1, len(parts), 2):
        ind = parts[i].strip().strip('.').upper().replace('O', '0')
        content = parts[i + 1] if i + 1 < len(parts) else ""

        m_just = PATTERNS['ind_justif'].search(content)
        m_nota = PATTERNS['ind_nota'].search(content)

        nota_raw = m_nota.group(1).strip() if m_nota else ""
        nota = normalize_nota(nota_raw)
        just_text = clean_justificativa(m_just.group(1)) if m_just else ""

        # Verifica "Não se Aplica"
        # Só marca como NSA se:
        #   a) a nota capturada for explicitamente N/A / NSA / etc., OU
        #   b) a justificativa for curta (< 60 chars) E contiver apenas essa frase
        nota_is_na = nota == "NSA"
        just_is_na = len(just_text) < 60 and bool(re.fullmatch(
            r'[\s\W]*(não\s+se\s+aplica|n/?a|nsa|n\.?a\.?)[\s\W]*', just_text, re.I
        ))
        is_na = nota_is_na or just_is_na
        if is_na:
            nota = "NSA"
            just_text = "Não se aplica"

        if just_text or nota:
            justificativas.append({
                'ID_DOCUMENTO':   pdf_name,
                'Curso':          meta['Curso'],
                'Id_MEC':         meta['Id_MEC'],
                'Ano_avaliacao':  meta['Ano_avaliacao'],
                'Modalidade':     meta['Modalidade'],
                'Cidade':         meta['Cidade'],
                'Campus':         meta['Campus'],
                'Indicador':      ind,
                'Nota_do_indicador': nota,
                'Justificativa':  just_text or "N/I",
            })

    justificativas.append({
        'ID_DOCUMENTO':   pdf_name,
        'Curso':          meta['Curso'],
        'Id_MEC':         meta['Id_MEC'],
        'Ano_avaliacao':  meta['Ano_avaliacao'],
        'Modalidade':     meta['Modalidade'],
        'Cidade':         meta['Cidade'],
        'Campus':         meta['Campus'],
        'Indicador':      'CONCEITO_FINAL_CONTINUO',
        'Nota_do_indicador': meta.get('CONCEITO_FINAL_CONTINUO', "N/I"),
        'Justificativa':  "N/A",
    })

    justificativas.append({
        'ID_DOCUMENTO':   pdf_name,
        'Curso':          meta['Curso'],
        'Id_MEC':         meta['Id_MEC'],
        'Ano_avaliacao':  meta['Ano_avaliacao'],
        'Modalidade':     meta['Modalidade'],
        'Cidade':         meta['Cidade'],
        'Campus':         meta['Campus'],
        'Indicador':      'CONCEITO_FINAL_FAIXA',
        'Nota_do_indicador': meta.get('CONCEITO_FINAL_FAIXA', "N/I"),
        'Justificativa':  "N/A",
    })

    return meta, justificativas

def extract_concepts_with_ocr(pdf_path: Path) -> str:
    if not OCR_AVAILABLE:
        return ""
    try:
        ocr = get_ocr()
        doc = fitz.open(pdf_path)
        page = doc[-1] # Ultima página onde os conceitos ficam
        pix = page.get_pixmap(dpi=150)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        
        result = ocr.ocr(img_array, cls=True)
        text_lines = []
        if result and result[0]:
            for line in result[0]:
                text_lines.append(line[1][0])
        return "\n".join(text_lines)
    except Exception as e:
        print(f"  [Erro OCR Conceitos] {pdf_path.name}: {e}")
        return ""

def processar_pdf(pdf_path: Path) -> tuple[dict, list[dict]]:
    try:
        # 1. Extrair texto inteiro do PDF
        text = extract_text(pdf_path, use_ocr=False)
        if len(text.strip()) < 100 and OCR_AVAILABLE:
            text = extract_text(pdf_path, use_ocr=True)
        
        normalized = normalize_text(text)
        meta, justificativas = parse(normalized, pdf_path.name)
        
        # Fallback para os conceitos caso sejam imagens
        if 'CONCEITO_FINAL_CONTINUO' not in meta or 'CONCEITO_FINAL_FAIXA' not in meta:
            ocr_text = extract_concepts_with_ocr(pdf_path)
            ocr_normalized = normalize_text(ocr_text)
            m_block = re.search(r"CONCEITO\s+FINAL\s+CONT[ÍI]NUO(.{0,150})", ocr_normalized, re.I | re.DOTALL)
            if m_block:
                block = m_block.group(1)
                nums = re.findall(r'\b\d(?:[.,]\d+)?\b', block)
                valid_nums = []
                for n in nums:
                    try:
                        v = float(n.replace(',', '.'))
                        if 1 <= v <= 5:
                            valid_nums.append(v)
                    except ValueError:
                        pass
                
                if len(valid_nums) >= 2:
                    meta['CONCEITO_FINAL_CONTINUO'] = valid_nums[0]
                    meta['CONCEITO_FINAL_FAIXA'] = int(valid_nums[1]) if valid_nums[1].is_integer() else valid_nums[1]
                elif len(valid_nums) == 1:
                    val = valid_nums[0]
                    if val.is_integer() and val >= 1:
                        meta['CONCEITO_FINAL_FAIXA'] = int(val)
                    else:
                        meta['CONCEITO_FINAL_CONTINUO'] = val
                        
                for j in justificativas:
                    if j['Indicador'] == 'CONCEITO_FINAL_CONTINUO':
                        j['Nota_do_indicador'] = meta.get('CONCEITO_FINAL_CONTINUO', 'N/I')
                    if j['Indicador'] == 'CONCEITO_FINAL_FAIXA':
                        j['Nota_do_indicador'] = meta.get('CONCEITO_FINAL_FAIXA', 'N/I')
                    
        return meta, justificativas

    except Exception as e:
        print(f"  [Erro ao processar] {pdf_path.name}: {e}")
        meta = {
            'ID_DOCUMENTO': pdf_path.name,
            'Curso': 'N/I', 'Id_MEC': 'N/I',
            'Ano_avaliacao': 'N/I', 'Modalidade': 'N/A',
            'Cidade': 'N/I', 'Campus': 'N/I'
        }
        return meta, []


def processar(diretorio: Path):
    pdfs = list(diretorio.glob("*.pdf"))
    print(f"\nIniciando extração de {len(pdfs)} arquivos PDF...\n")

    metas = []
    justifs = []

    # Processamento sequencial: PaddleOCR carrega ~500MB+ de modelos na RAM.
    # Com ProcessPoolExecutor cada worker duplicava esse peso, estourando a memória.
    for pdf_path in tqdm(pdfs, desc="Processando"):
        m, j = processar_pdf(pdf_path)
        metas.append(m)
        justifs.extend(j)

    if justifs:
        pd.DataFrame(justifs).to_json(
            config.OUTPUT_RELATORIO_JSON,
            orient='records', indent=2, force_ascii=False
        )
        print(f"Relatório salvo: {config.OUTPUT_RELATORIO_JSON}")

    print(f"\nConcluido. {len(justifs)} registros extraidos de {len(metas)} PDFs.")

    # Diagnóstico de qualidade / Cobertura
    if metas:
        campos_criticos = ['Id_MEC', 'Curso', 'Ano_avaliacao', 'Modalidade', 'Cidade', 'CONCEITO_FINAL_CONTINUO', 'CONCEITO_FINAL_FAIXA']
        df_meta = pd.DataFrame(metas)
        cobertura = {}
        for col in campos_criticos:
            if col in df_meta.columns:
                valid_count = df_meta[col].notna() & (df_meta[col] != "N/I") & (df_meta[col] != "N/A")
                cobertura[col] = valid_count.mean() * 100
            else:
                cobertura[col] = 0.0

        print("\n=== Cobertura de campos críticos ===")
        for col, val in cobertura.items():
            print(f"  {col}: {val:.2f}%")


# ==============================================================================
# EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    processar(config.INPUT_DIR)
