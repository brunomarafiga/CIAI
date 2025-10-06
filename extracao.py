import re
import concurrent.futures
from pathlib import Path
import pandas as pd
from pypdf import PdfReader

# --- CONFIGURAÇÃO ---
INPUT_DIR = Path(__file__).parent
OUTPUT_CSV_FILE = 'relatorio_consolidado_extraido.csv'
# --- FIM DA CONFIGURAÇÃO ---


def extrair_texto_do_pdf(pdf_path: Path) -> str:
    """
    Extrai texto de um PDF usando pypdf.
    """
    print(f"  Extraindo texto de '{pdf_path.name}'...")
    try:
        reader = PdfReader(pdf_path)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text() or ""
            texto_completo += "\n\n"
        return texto_completo
    except Exception as e:
        print(f"    -> Falha ao extrair texto de '{pdf_path.name}': {e}")
        return ""


def extrair_informacoes(texto: str, pdf_path: Path) -> dict:
    """
    Usa expressões regulares aprimoradas para extrair dados do texto do relatório.
    """
    dados = {}

    # --- Extração do Curso e Código ---
    # Use lookahead to stop before the next section
    nome_curso_match = re.search(r"Curso\(s\)\s*/\s*Habilitação\(ões\)[^\n]*?:\s*(.*?)(?=\s*Informações da comissão:)", texto, re.DOTALL | re.IGNORECASE)
    
    if nome_curso_match and nome_curso_match.group(1).strip():
        nome_curso = nome_curso_match.group(1).strip()
    else:
        # Fallback to filename if course name is not found
        nome_curso = pdf_path.stem.replace("Ocr_", "").replace("Relatório ", "").strip()

    codigo_match = re.search(r"C[oó]digo (?:(?:e-MEC )?do Curso|MEC)\s*:\s*(\d+)", texto, re.IGNORECASE)
    codigo_mec = codigo_match.group(1).strip() if codigo_match else None

    if codigo_mec:
        dados['CURSO'] = f"{codigo_mec} - {nome_curso}"
    else:
        dados['CURSO'] = nome_curso

    # --- Extração de outros dados ---
    conceitos_match = re.search(r"CONCEITO\s+FINAL\s+CONTÍNUO\s+CONCEITO\s+FINAL\s+FAIXA\s+([\d,.]+)\s+(\d)", texto, re.IGNORECASE)
    if conceitos_match:
        dados['CONCEITO FINAL CONTÍNUO'] = conceitos_match.group(1).strip().replace(',', '.')
        dados['CONCEITO FINAL FAIXA'] = conceitos_match.group(2).strip()
    else:
        dados['CONCEITO FINAL CONTÍNUO'] = None
        dados['CONCEITO FINAL FAIXA'] = None

    bloco_avaliadores_match = re.search(r'Avaliadores\s*"ad-hoc":\s*(.*?)(?:\n\n|\Z)', texto, re.DOTALL)
    if bloco_avaliadores_match:
        bloco_texto = bloco_avaliadores_match.group(1)
        # Remove role descriptions like "-> coordenador(a) da comissão"
        bloco_limpo = re.sub(r'->.*?comissão', '', bloco_texto)
        # Split the string by the CPF pattern to get the names
        nomes_brutos = re.split(r'\s*\(\d+\)', bloco_limpo)
        # Clean up the found names
        nomes_limpos = [nome.strip() for nome in nomes_brutos if len(nome.strip()) > 5]
        dados['Avaliador 1'] = nomes_limpos[0] if len(nomes_limpos) > 0 else ''
        dados['Avaliador 2'] = nomes_limpos[1] if len(nomes_limpos) > 1 else ''
    else:
        dados['Avaliador 1'] = ''
        dados['Avaliador 2'] = ''

    # Notas dos Indicadores
    # Split the text by a more specific indicator pattern to handle formatting errors
    blocos = re.split(r'(?=(?:[123])\.\d{1,2}\.)', texto)
    
    for bloco in blocos:
        # Find the indicator and grade within each block
        match = re.search(r"(\d+\.\d+)\..*?Justificativa para conceito\s*(.*?)\s*:", bloco, re.DOTALL | re.IGNORECASE)
        if match:
            indicador, nota = match.groups()
            nota_limpa = nota.strip()
            if nota_limpa.upper() == 'NSA':
                dados[indicador] = 'nsa'
            elif nota_limpa.isdigit():
                dados[indicador] = nota_limpa

    return dados


def processar_um_arquivo(pdf_path: Path):
    """Processa um único arquivo PDF e retorna os dados extraídos."""
    print(f"Processando: {pdf_path.name}...")
    texto = extrair_texto_do_pdf(pdf_path)
    if texto:
        info = extrair_informacoes(texto, pdf_path)
        print(f"  -> Informações extraídas para: {info.get('CURSO', 'N/A')}")
        return info
    return None


def processar_arquivos_em_paralelo():
    """
    Função principal que orquestra a leitura dos PDFs e a criação do CSV em paralelo.
    """
    pdf_files = list(INPUT_DIR.glob('**/*.pdf'))
    if not pdf_files:
        print(f"Nenhum PDF para processar encontrado em '{INPUT_DIR.resolve()}'.")
        return

    print(f"Encontrados {len(pdf_files)} PDFs para processar.")

    lista_de_dados = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
        resultados = executor.map(processar_um_arquivo, pdf_files)
        lista_de_dados = [r for r in resultados if r is not None]

    if not lista_de_dados:
        print("Nenhuma informação foi extraída. Finalizando.")
        return

    df = pd.DataFrame(lista_de_dados)

    # --- Estrutura do CSV ---
    df_cols = ['CURSO']
    for i in range(1, 25): df_cols.append(f'1.{i}')
    df_cols.append('BLANK_1')
    for i in range(1, 17): df_cols.append(f'2.{i}')
    for i in range(1, 18): df_cols.append(f'3.{i}')
    df_cols.extend(['CONCEITO FINAL CONTÍNUO', 'CONCEITO FINAL FAIXA', 'Avaliador 1', 'Avaliador 2'])

    df['BLANK_1'] = ''
    df = df.reindex(columns=df_cols)
    
    indicator_cols = [col for col in df.columns if '.' in col]
    df[indicator_cols] = df[indicator_cols].fillna('')

    header = (
        ";DIMENSÃO;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;\n"
        "CURSO; 1. ORGANIZAÇÃO DIDÁTICO-PEDAGÓGICA;;;;;;;;;;;;;;;;;;;;;;;;;2. CORPO DOCENTE E TUTORIAL;;;;;;;;;;;;;;;;3. INFRAESTRUTURA;;;;;;;;;;;;;;;;;CONCEITO FINAL CONTÍNUO;CONCEITO FINAL FAIXA;Avaliador 1;Avaliador 2\n"
        ";INDICADOR;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;\n"
        ";1.1;1.2;1.3;1.4;1.5;1.6;1.7;1.8;1.9;1.10;1.11;1.12;1.13;1.14;1.15;1.16;1.17;1.18;1.19;1.20;1.21;1.22;1.23;1.24;;2.1;2.2;2.3;2.4;2.5;2.6;2.7;2.8;2.9;2.10;2.11;2.12;2.13;2.14;2.15;2.16;3.1;3.2;3.3;3.4;3.5;3.6;3.7;3.8;3.9;3.10;3.11;3.12;3.13;3.14;3.15;3.16;3.17;;;\n"
    )

    with open(OUTPUT_CSV_FILE, 'w', encoding='utf-8', newline='') as f:
        f.write(header)
    
    df.to_csv(OUTPUT_CSV_FILE, sep=';', index=False, decimal=',', header=False, mode='a', encoding='utf-8')

    print(f"\nProcessamento concluído! Arquivo consolidado salvo em: '{OUTPUT_CSV_FILE}'")


if __name__ == '__main__':
    processar_arquivos_em_paralelo()
