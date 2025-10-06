import os
import re
import csv
import fitz  # PyMuPDF

def _obter_resumo_setor(texto, palavras_chave_publica, palavras_chave_privada, tipo):
    """Analisa um bloco de texto e retorna um resumo sobre a predominância do setor."""
    if not texto or not texto.strip():
        return "Informação não encontrada"

    texto_lower = texto.lower()
    contagem_publica = sum(texto_lower.count(kw) for kw in palavras_chave_publica)
    contagem_privada = sum(texto_lower.count(kw) for kw in palavras_chave_privada)

    prefixo = "Formação" if tipo == "formacao" else "Atuação profissional"

    if contagem_publica > contagem_privada:
        return f"{prefixo} majoritariamente no setor Público"
    elif contagem_privada > contagem_publica:
        return f"{prefixo} majoritariamente no setor Privado"
    elif contagem_publica > 0 and contagem_publica == contagem_privada:
        return f"{prefixo} com presença equilibrada nos setores Público e Privado"
    else:
        return "Não foi possível determinar o setor predominante"

def extrair_informacoes_lattes(pasta_pdfs):
    """
    Extrai informações de currículos Lattes em formato PDF.

    Argumentos:
        pasta_pdfs (str): O caminho para a pasta contendo os arquivos PDF.

    Retorna:
        list: Uma lista de dicionários, onde cada dicionário contém as
              informações extraídas de um currículo.
    """
    dados_extraidos = []
    palavras_chave_publica = [
        'universidade federal', 'instituto federal', 'secretaria de estado',
        'prefeitura', 'fundação de amparo', 'empresa brasileira de',
        'governo do estado', 'ministério', 'ufrj', 'ufrn', 'ufba', 'ufmg',
        'usp', 'unicamp', 'unesp', 'fiocruz', 'uab'
    ]
    palavras_chave_privada = [
        'puc', 'mackenzie', 'fgv', 'estácio', 'unip', 'anhanguera', 'unopar',
        'kroton', 'ser educacional', 'wyden', 'ibmec', 'dom cabral', 'faculdade',
        'centro universitário', 'universidade paulista', 'getulio vargas'
    ]
    grandes_areas_cnpq = [
        "Ciências Exatas e da Terra", "Ciências Biológicas", "Engenharias",
        "Ciências da Saúde", "Ciências Agrárias", "Ciências Sociais Aplicadas",
        "Ciências Humanas", "Linguística, Letras e Artes",
    ]

    for nome_arquivo in os.listdir(pasta_pdfs):
        if nome_arquivo.lower().endswith(".pdf"):
            caminho_completo = os.path.join(pasta_pdfs, nome_arquivo)
            print(f"Processando arquivo: {nome_arquivo}")

            try:
                with fitz.open(caminho_completo) as doc:
                    texto_completo = "".join(pagina.get_text("text") for pagina in doc)

                # Extração do nome
                nome_pesquisador = "Nome não encontrado"
                match_nome_arquivo = re.search(r'\((.*?)\)', nome_arquivo)
                if match_nome_arquivo:
                    nome_pesquisador = match_nome_arquivo.group(1)
                elif texto_completo:
                    nome_pesquisador = texto_completo.split('\n')[0].strip()

                # Extração do link do Lattes
                match_link = re.search(r'https?://lattes\.cnpq\.br/\d+', texto_completo)
                link_lattes = match_link.group(0) if match_link else "Link não encontrado"

                # Extração e normalização da Grande Área de Formação
                area_formacao = "Não encontrada"
                match_area_linha = re.search(r'Grande área:\s*([^\n]*)', texto_completo, re.IGNORECASE)
                if match_area_linha:
                    linha_area = match_area_linha.group(1).strip()
                    for area in grandes_areas_cnpq:
                        if re.search(r'\b' + re.escape(area) + r'\b', linha_area, re.IGNORECASE):
                            area_formacao = area
                            break
                    if area_formacao == "Não encontrada":
                        area_formacao = linha_area.split('/')[0].strip()

                # Processamento para resumos de Formação e Atuação
                texto_processado = re.sub(r'\s+', ' ', texto_completo.replace('\n', ' '))
                
                # Resumo da Formação
                bloco_formacao = ""
                match_formacao = re.search(r'Formação Acadêmica/Titulação(.*?)Atuação Profissional', texto_processado, re.DOTALL | re.IGNORECASE)
                if match_formacao:
                    bloco_formacao = match_formacao.group(1)
                resumo_formacao = _obter_resumo_setor(bloco_formacao, palavras_chave_publica, palavras_chave_privada, "formacao")

                # Resumo da Atuação
                bloco_atuacao = ""
                match_atuacao = re.search(r'Atuação Profissional(.*?)Projetos de pesquisa', texto_processado, re.DOTALL | re.IGNORECASE)
                if not match_atuacao:
                    match_atuacao = re.search(r'Atuação Profissional(.*?)Áreas de atuação', texto_processado, re.DOTALL | re.IGNORECASE)
                if match_atuacao:
                    bloco_atuacao = match_atuacao.group(1)
                resumo_atuacao = _obter_resumo_setor(bloco_atuacao, palavras_chave_publica, palavras_chave_privada, "atuacao")

                dados_pesquisador = {
                    "Nome": nome_pesquisador,
                    "Link Lattes": link_lattes,
                    "Principal Área de Formação": area_formacao,
                    "Formação Acadêmica/Titulação": resumo_formacao,
                    "Atuação Profissional": resumo_atuacao,
                }
                dados_extraidos.append(dados_pesquisador)

            except Exception as e:
                print(f"Erro ao processar o arquivo {nome_arquivo}: {e}")

    return dados_extraidos

def salvar_csv(dados, nome_arquivo_saida):
    """
    Salva os dados extraídos em um arquivo CSV.
    """
    if not dados:
        print("Nenhum dado para salvar.")
        return

    print(f"Salvando dados em {nome_arquivo_saida}...")
    try:
        with open(nome_arquivo_saida, 'w', newline='', encoding='utf-8-sig') as arquivo_csv:
            campos = ["Nome", "Link Lattes", "Principal Área de Formação", "Formação Acadêmica/Titulação", "Atuação Profissional"]
            writer = csv.DictWriter(arquivo_csv, fieldnames=campos)
            writer.writeheader()
            writer.writerows(dados)
        print("Arquivo CSV salvo com sucesso!")
    except PermissionError:
        print(f"\nERRO: Permissão negada para escrever no arquivo '{nome_arquivo_saida}'.")
        print("Por favor, feche o arquivo se ele estiver aberto em outro programa (como o Excel) e tente novamente.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao salvar o CSV: {e}")


if __name__ == '__main__':
    pasta_lattes = '.'
    arquivo_saida = 'extracao_lattes_resultado.csv'

    if not os.path.isdir(pasta_lattes):
        print(f"Erro: A pasta '{pasta_lattes}' não foi encontrada.")
    else:
        dados_finais = extrair_informacoes_lattes(pasta_lattes)
        salvar_csv(dados_finais, arquivo_saida)