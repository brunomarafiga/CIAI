import re
import os
import concurrent.futures
from pathlib import Path
import pandas as pd
from pypdf import PdfReader

# --- CONFIGURAÇÃO ---
INPUT_DIR = Path(__file__).parent
OUTPUT_CSV_FILE = 'relatorio_consolidado_extraido.csv'
MAX_CPU_WORKERS = os.cpu_count()  # Usar todos os núcleos de CPU disponíveis
# --- FIM DA CONFIGURAÇÃO ---

# --- PADRÕES DE REGEX PRÉ-COMPILADOS ---
# Padrão para o nome do curso (preservando quebras de linha se necessário, mas aqui simplificado)
NOME_CURSO_PATTERN = re.compile(r"Denominação do Curso:\s*(.*?);", re.IGNORECASE)
CODIGO_MEC_PATTERN = re.compile(r"Cód\. Curso:\s*(\d+)", re.IGNORECASE)

# Novos padrões
ANO_AVALIACAO_PATTERN = re.compile(r"ocorreu no per[íi]odo compreendido entre.*? de (\d{4})", re.IGNORECASE | re.DOTALL)
CIDADE_PATTERN = re.compile(r"CEP[;:]?\s*[\d.-]+,\s*([^-]+)-[A-Z]{2}", re.IGNORECASE)
# Campus: captura até a vírgula antes de 'situado'
CAMPUS_PATTERN = re.compile(r"Campus\s+([^,]+),\s*situado", re.IGNORECASE)
# Modalidade: captura o Grau (Licenciatura/Bacharelado)
MODALIDADE_PATTERN = re.compile(r"Grau:\s*([^;]+)", re.IGNORECASE)

CONCEITO_CONTINUO_PATTERN = re.compile(r"CONCEITO FINAL CONTÍNUO\s*([\d,]+)", re.IGNORECASE)
CONCEITO_FAIXA_PATTERN = re.compile(r"CONCEITO FINAL FAIXA\s*(\d+)", re.IGNORECASE)

# Padrão para indicadores (ex: 1.1, 2.3, 3.12)
# Captura o número do indicador e a nota (ou NSA) antes de "Justificativa"
INDICADOR_PATTERN = re.compile(r"(\d+\.\d+)\.\s+.*?\s(\d|NSA)\s+Justificativa", re.IGNORECASE | re.DOTALL)
# --- FIM DOS PADRÕES ---


def extrair_texto_do_pdf(pdf_path: Path) -> str:
    """
    Extrai texto de um PDF usando pypdf.
    """
    try:
        reader = PdfReader(pdf_path)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text() or ""
            texto_completo += "\n"
        return texto_completo
    except Exception as e:
        print(f"    -> Falha ao extrair texto de '{pdf_path.name}': {e}")
        return ""


def extrair_informacoes(texto: str, pdf_path: Path) -> dict:
    """
    Usa expressões regulares para extrair dados do texto do relatório.
    """
    dados = {}
    
    # Limpeza básica: normaliza múltiplos espaços para um único espaço
    texto_limpo_para_regex = re.sub(r'\s+', ' ', texto).strip()

    # --- Extração do Curso e Código ---
    # Usamos o texto original ou limpo dependendo da complexidade do padrão
    # Aqui vamos usar o limpo para garantir consistência
    
    nome_curso_match = NOME_CURSO_PATTERN.search(texto_limpo_para_regex)
    dados['Curso'] = nome_curso_match.group(1).strip() if nome_curso_match else 'NÃO ENCONTRADO'

    codigo_match = CODIGO_MEC_PATTERN.search(texto_limpo_para_regex)
    dados['Id_MEC'] = codigo_match.group(1).strip() if codigo_match else ''

    # --- Extração de Ano, Cidade, Campus, Modalidade ---
    ano_match = ANO_AVALIACAO_PATTERN.search(texto_limpo_para_regex)
    dados['Ano_avaliacao'] = ano_match.group(1).strip() if ano_match else ''

    cidade_match = CIDADE_PATTERN.search(texto_limpo_para_regex)
    dados['Cidade'] = cidade_match.group(1).strip() if cidade_match else ''

    campus_match = CAMPUS_PATTERN.search(texto_limpo_para_regex)
    dados['Campus'] = campus_match.group(1).strip() if campus_match else ''

    modalidade_match = MODALIDADE_PATTERN.search(texto_limpo_para_regex)
    dados['Modalidade'] = modalidade_match.group(1).strip() if modalidade_match else ''

    # --- Extração de Conceitos ---
    conc_cont_match = CONCEITO_CONTINUO_PATTERN.search(texto_limpo_para_regex)
    dados['CONCEITO FINAL CONTÍNUO'] = conc_cont_match.group(1).strip().replace('.', ',') if conc_cont_match else ''

    conc_faixa_match = CONCEITO_FAIXA_PATTERN.search(texto_limpo_para_regex)
    dados['CONCEITO FINAL FAIXA'] = conc_faixa_match.group(1).strip() if conc_faixa_match else ''

    # --- Notas dos Indicadores ---
    # Encontrar todos os indicadores
    matches = INDICADOR_PATTERN.findall(texto_limpo_para_regex)
    for indicador, nota in matches:
        nota_limpa = nota.strip()
        if nota_limpa.upper() == 'NSA':
            dados[indicador] = '' # Deixar vazio ou 'NSA' conforme preferência. O usuário pediu vazio no exemplo visual? 
                                  # O exemplo mostrava vazios. Vamos manter vazio se for NSA ou se não tiver nota.
                                  # Mas se o regex capturou NSA, é NSA.
                                  # O exemplo do usuário tem células vazias.
                                  # Se for NSA, vou deixar vazio para alinhar com o exemplo visual que tem buracos.
                                  # Mas espere, o exemplo do usuário tem notas 5, 4, 3... e células vazias.
                                  # Se o regex capturar 'NSA', vou colocar vazio.
            dados[indicador] = ''
        elif nota_limpa.isdigit():
            dados[indicador] = nota_limpa

    return dados


def processar_um_arquivo(pdf_path: Path):
    """Processa um único arquivo PDF e retorna os dados extraídos."""
    print(f"Processando: {pdf_path.name}...")
    texto = extrair_texto_do_pdf(pdf_path)
    if texto:
        info = extrair_informacoes(texto, pdf_path)
        # print(f"  -> Informações extraídas para: {info.get('Curso', 'N/A')}")
        return info
    return None


def processar_arquivos_em_paralelo():
    """
    Função principal que orquestra a leitura dos PDFs e a criação do CSV em paralelo.
    """
    pdf_files = list(INPUT_DIR.glob('*.pdf'))
    if not pdf_files:
        print(f"Nenhum PDF para processar encontrado em '{INPUT_DIR.resolve()}'.")
        return

    print(f"Encontrados {len(pdf_files)} PDFs para processar. Usando até {MAX_CPU_WORKERS} processos.")

    lista_de_dados = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_CPU_WORKERS) as executor:
        resultados = executor.map(processar_um_arquivo, pdf_files)
        lista_de_dados = [r for r in resultados if r is not None]

    if not lista_de_dados:
        print("Nenhuma informação foi extraída. Finalizando.")
        return

    df = pd.DataFrame(lista_de_dados)

    # --- Estrutura do CSV ---
    # Colunas fixas iniciais
    fixed_cols_start = ['Curso', 'Id_MEC', 'Ano_avaliacao', 'Modalidade', 'Cidade', 'Campus']
    
    # Colunas de indicadores
    ind_1 = [f'1.{i}' for i in range(1, 25)]
    ind_2 = [f'2.{i}' for i in range(1, 17)]
    ind_3 = [f'3.{i}' for i in range(1, 18)]
    
    # Colunas finais
    fixed_cols_end = ['CONCEITO FINAL CONTÍNUO', 'CONCEITO FINAL FAIXA']
    
    # Monta a lista completa de colunas na ordem desejada
    all_cols = fixed_cols_start + ind_1 + ind_2 + ind_3 + fixed_cols_end
    
    # Garante que todas as colunas existam no DataFrame (preenchendo com vazio se não existirem)
    for col in all_cols:
        if col not in df.columns:
            df[col] = ''
            
    # Reordena as colunas e preenche NaNs com vazio
    df = df.reindex(columns=all_cols).fillna('')

    # Salva o CSV
    # Usando sep=';' e encoding='utf-8-sig' para compatibilidade com Excel no Brasil
    df.to_csv(OUTPUT_CSV_FILE, sep=';', index=False, encoding='utf-8-sig')

    print(f"\nProcessamento concluído! Arquivo consolidado salvo em: '{OUTPUT_CSV_FILE}'")


if __name__ == '__main__':
    processar_arquivos_em_paralelo()
