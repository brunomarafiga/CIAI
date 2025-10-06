import re
import concurrent.futures
from pathlib import Path
import pandas as pd
from pypdf import PdfReader

# --- CONFIGURAÇÃO ---
INPUT_DIR = Path(__file__).parent
OUTPUT_CSV_FILE = 'relatorio_justificativas.csv'
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


def extrair_informacoes(texto: str) -> list[dict]:
    """
    Usa expressões regulares para extrair o nome do curso e as justificativas de cada indicador.
    Retorna uma lista de dicionários, cada um representando uma linha do CSV final.
    """
    # --- Extração do Curso e Código ---
    nome_curso_match = re.search(r"Curso\(s\)\s*/\s*Habilitação\(ões\)[^\n]*?:\s*([^\n]+)", texto, re.IGNORECASE)
    nome_curso = nome_curso_match.group(1).strip() if nome_curso_match else 'NÃO ENCONTRADO'

    codigo_match = re.search(r"C[oó]digo (?:(?:e-MEC )?do Curso|MEC)\s*:\s*(\d+)", texto, re.IGNORECASE)
    codigo_mec = codigo_match.group(1).strip() if codigo_match else ''
    
    curso_completo = f"{codigo_mec} - {nome_curso}" if codigo_mec else nome_curso

    lista_justificativas = []
    
    # Encontra o início de cada bloco de indicador
    # Usamos re.split para dividir o texto em blocos para cada indicador
    blocos = re.split(r'(?=^\s*\d+\.\d+\.)', texto, flags=re.MULTILINE)

    for bloco in blocos:
        # Pega o número do indicador do início do bloco
        indicador_match = re.match(r'^\s*(\d+\.\d+)\.', bloco)
        if not indicador_match:
            continue
        
        indicador_num = indicador_match.group(1)

        # Extrai a justificativa do bloco
        justificativa_match = re.search(r"Justificativa para conceito.*?:(.*?)(?=\Z)", bloco, re.IGNORECASE | re.DOTALL)
        
        if justificativa_match:
            # Limpa o texto da justificativa, removendo quebras de linha e espaços extras
            justificativa_texto = ' '.join(justificativa_match.group(1).split())
            
            dados_linha = {
                'CURSO': curso_completo,
                'INDICADOR': indicador_num,
                'JUSTIFICATIVA': justificativa_texto
            }
            lista_justificativas.append(dados_linha)

    return lista_justificativas


def processar_um_arquivo(pdf_path: Path) -> list[dict] | None:
    """Processa um único arquivo PDF e retorna os dados extraídos."""
    print(f"Processando: {pdf_path.name}...")
    texto = extrair_texto_do_pdf(pdf_path)
    if texto:
        info = extrair_informacoes(texto)
        print(f"  -> {len(info)} justificativas extraídas para: {info[0]['CURSO'] if info else 'N/A'}")
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

    lista_completa_dados = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
        # executor.map agora retorna uma lista de listas de dicionários
        resultados_por_arquivo = executor.map(processar_um_arquivo, pdf_files)
        for resultado_arquivo in resultados_por_arquivo:
            if resultado_arquivo:
                lista_completa_dados.extend(resultado_arquivo)

    if not lista_completa_dados:
        print("Nenhuma informação foi extraída. Finalizando.")
        return

    df = pd.DataFrame(lista_completa_dados)
    
    # Salva o DataFrame no formato CSV longo
    df.to_csv(OUTPUT_CSV_FILE, sep=';', index=False, encoding='utf-8')

    print(f"\nProcessamento concluído! Arquivo consolidado salvo em: '{OUTPUT_CSV_FILE}'")


if __name__ == '__main__':
    processar_arquivos_em_paralelo()
