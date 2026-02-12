import re
import pandas as pd
import google.generativeai as genai
from tqdm import tqdm
import time
import json
import os

# ==========================================
# CONFIGURAÇÃO
# ==========================================

# 1. COLOQUE SUA API KEY DO GEMINI AQUI
GOOGLE_API_KEY = "AIzaSyBdxeibulQKkm5XxdTLqb-uwXp7CwSPjT8" 

# Configuração da IA
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-3-flash-preview')

# Caminhos dos arquivos (Ajustados para a nova estrutura de pastas)
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # src/
PROJECT_ROOT = os.path.dirname(BASE_DIR)              # root/

ARQUIVO_ENTRADA = os.path.join(PROJECT_ROOT, 'data', 'justificativas_notas_baixas.txt')
ARQUIVO_SAIDA_CSV = os.path.join(PROJECT_ROOT, 'data', 'tabela_dados_processados.csv')
ARQUIVO_SAIDA_TXT = os.path.join(PROJECT_ROOT, 'reports', 'log_analise_ia.txt')

# Definição das Categorias SUGERIDAS (mas não limitantes)
CATEGORIAS_SUGERIDAS = [
    "Formalização da Inovação e Diferenciação",
    "Gestão e Feedback",
    "Infraestrutura e Acessibilidade",
    "Corpo Docente e Tutorial",
    "Projeto Pedagógico e Curricular",
    "Desempenho e Avaliação Discente"
]

# ==========================================
# 1. FUNÇÃO DE ANÁLISE COM GEMINI
# ==========================================
def analisar_justificativa(texto, nota, curso):
    prompt = f"""
    Você é um especialista em avaliação do MEC/INEP. O objetivo é identificar as FRAGILIDADES que levaram à nota baixa (<5).
    
    Analise a JUSTIFICATIVA para o curso {curso} (Nota: {nota}):
    "{texto}"
    
    TAREFAS:
    1. Identifique os PONTOS NEGATIVOS ou CRITÉRIOS NÃO ATENDIDOS citados no texto (ex: acervo desatualizado, falta de laboratórios, PPC incoerente). Seja específico.
    
    2. Classifique a justificativa na categoria mais adequada.
       Você pode usar uma das categorias sugeridas abaixo OU criar uma nova categoria que descreva melhor o problema principal.
       CATEGORIAS SUGERIDAS: {CATEGORIAS_SUGERIDAS}
       
    3. Gere 3 tags técnicas focadas nos problemas (ex: #bibliografia_desatualizada, #infraestrutura_precaria).
    
    FORMATO DE RESPOSTA (JSON APENAS):
    {{
        "pontos_negativos": "Resumo conciso das fragilidades identificadas",
        "categoria": "Nome da Categoria (Sugerida ou Nova)",
        "tags": ["#tag1", "#tag2", "#tag3"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Limpeza robusta para extrair JSON
        raw_text = response.text
        # Tenta encontrar o bloco JSON
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            clean_text = json_match.group(0)
            data = json.loads(clean_text)
            return data.get('categoria', "Não Categorizado"), data.get('tags', []), data.get('pontos_negativos', "Não identificado")
        else:
             return "Erro Formato", ["#erro"], "Erro ao processar JSON"
             
    except Exception as e:
        print(f"Erro na IA: {e}")
        return "Erro API", [], "Erro na chamada API"

# ==========================================
# 2. PARSER (LEITURA DO ARQUIVO)
# ==========================================
def processar_arquivo(caminho_arquivo):
    # LER COM UTF-8 POIS O ARQUIVO FONTE É UTF-8
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    dados = []
    
    curr_indicador = None
    curr_setor = None
    curr_curso_info = {}
    capturing_text = False
    buffer_text = []

    # Regex patterns (Ajustados para maior flexibilidade)
    pat_indicador = re.compile(r'^\s*INDICADOR:\s*(.*)', re.IGNORECASE)
    # Ajuste: Captura tudo até o parametro (Qtd:, permitindo espaços extras
    pat_setor = re.compile(r'^\s*LOCALIZAÇÃO/SETOR:\s*(.*?)\s*\(Qtd:', re.IGNORECASE)
    # Ajuste: Captura Nota, Nome do Curso e ID com flexibilidade
    pat_curso = re.compile(r'^\s*\[Nota:\s*([\d,]+)\]\s*(.*?)\s*-\s*ID:\s*(\d+)', re.IGNORECASE)
    pat_separator = re.compile(r'^-+$|^=+$')

    for line in tqdm(lines, desc="Lendo Arquivo"):
        line_stripped = line.strip()
        
        # 1. Detecta Indicador
        if match := pat_indicador.match(line_stripped):
            curr_indicador = match.group(1).strip()
            continue

        # 2. Detecta Setor
        if match := pat_setor.match(line_stripped):
            curr_setor = match.group(1).strip()
            continue

        # 3. Detecta Início de Curso
        if match := pat_curso.match(line_stripped):
            # Se já tínhamos um curso sendo capturado, salva ele antes de começar o novo
            if curr_curso_info:
                dados.append({
                    'Indicador': curr_indicador,
                    'Setor': curr_setor,
                    'Curso': curr_curso_info['nome'],
                    'Nota': curr_curso_info['nota'],
                    'ID': curr_curso_info['id'],
                    'Justificativa': " ".join(buffer_text).strip()
                })
            
            # Inicia novo bloco
            curr_curso_info = {
                'nota': match.group(1),
                'nome': match.group(2).strip(),
                'id': match.group(3)
            }
            buffer_text = []
            capturing_text = True
            continue

        # 4. Captura de Texto da Justificativa
        if capturing_text:
            # Ignora linhas de separação, hashtags manuais ou linhas vazias que parecem separadores
            if pat_separator.match(line_stripped) or line_stripped.startswith('#'):
                continue
            
            # Se encontrar um novo indicador ou setor, para a captura (segurança)
            if pat_indicador.match(line_stripped) or pat_setor.match(line_stripped):
                capturing_text = False
                continue

            if line_stripped: # Se não for vazia
                buffer_text.append(line_stripped)

    # Adiciona o último registro pendente
    if curr_curso_info:
         dados.append({
            'Indicador': curr_indicador,
            'Setor': curr_setor,
            'Curso': curr_curso_info['nome'],
            'Nota': curr_curso_info['nota'],
            'ID': curr_curso_info['id'],
            'Justificativa': " ".join(buffer_text).strip()
        })

    return pd.DataFrame(dados)

# ==========================================
# 3. PROCESSAMENTO E ANÁLISE
# ==========================================

def testar_api():
    print("\n--- TESTE DE CONEXÃO COM A API ---")
    try:
        response = model.generate_content("Responda 'OK' se estiver me ouvindo.")
        print(f"Resposta da API: {response.text.strip()}")
        print("Conexão BEM SUCEDIDA!\n")
        return True
    except Exception as e:
        print(f"FALHA NA CONEXÃO COM A API: {e}")
        return False

# CARREGAR DADOS DE ENTRADA
df = processar_arquivo(ARQUIVO_ENTRADA)
print(f"Total de registros no arquivo de entrada: {len(df)}")

# VERIFICAR DADOS JÁ PROCESSADOS
processados_set = set()
if os.path.exists(ARQUIVO_SAIDA_CSV):
    try:
        df_existente = pd.read_csv(ARQUIVO_SAIDA_CSV, sep=';', encoding='utf-8-sig')
        # Criar chave composta: ID + INDICADOR
        if 'ID' in df_existente.columns and 'Indicador' in df_existente.columns:
            # Converter para string e remover espaços extras para garantir match
            for _, row in df_existente.iterrows():
                chave = (str(row['ID']).strip(), str(row['Indicador']).strip())
                processados_set.add(chave)
        print(f"Registros já processados encontrados: {len(processados_set)}")
    except Exception as e:
        print(f"Aviso: Não foi possível ler o arquivo existente ({e}). Iniciando do zero.")

# FILTRAR APENAS O QUE AINDA NÃO FOI PROCESSADO
# Garante que as colunas sejam strings limpas para comparação
df['ID'] = df['ID'].astype(str).str.strip()
df['Indicador'] = df['Indicador'].astype(str).str.strip()

# Função auxiliar para verificar se a linha já foi processada
def ja_processado(row):
    chave = (str(row['ID']), str(row['Indicador']))
    return chave in processados_set

# Aplica o filtro
df_para_processar = df[~df.apply(ja_processado, axis=1)]
print(f"Registros restantes para processar: {len(df_para_processar)}")

if len(df_para_processar) == 0:
    print("Todos os registros já foram processados! Gerando relatório final...")
else:
    if not testar_api():
        print("Abortando devido a erro na API.")
        exit()

    print("Iniciando análise com Gemini AI (Isso pode levar alguns minutos)...")

    # Loop para processar e salvar INCREMENTALMENTE
    for index, row in tqdm(df_para_processar.iterrows(), total=df_para_processar.shape[0], desc="Analisando com IA"):
        cat, tags, p_neg = analisar_justificativa(row['Justificativa'], row['Nota'], row['Curso'])
        
        # Cria um DataFrame com UMA linha contendo os dados processados
        row_processed = row.to_dict()
        row_processed['Categoria_Bardin'] = cat
        # Convert tags to string representation for CSV storage
        row_processed['Tags_IA'] = json.dumps(tags, ensure_ascii=False) 
        row_processed['Pontos_Negativos'] = p_neg
        
        df_row = pd.DataFrame([row_processed])
        
        # Salva no CSV (append mode)
        # Se for o primeiro registro do arquivo (arquivo não existia ou estava vazio antes do loop), escreve cabeçalho
        # Mas cuidado: se arquivo já existia com outros IDs, não escreve cabeçalho
        file_exists = os.path.isfile(ARQUIVO_SAIDA_CSV) and os.path.getsize(ARQUIVO_SAIDA_CSV) > 0
        df_row.to_csv(ARQUIVO_SAIDA_CSV, mode='a', index=False, sep=';', encoding='utf-8-sig', header=not file_exists)
        
        time.sleep(1) # Pausa para evitar estourar limite da API gratuita

# ==========================================
# 4. GERAÇÃO DO CABEÇALHO E RELATÓRIO FINAL
# ==========================================

print("\nGerando relatório consolidado a partir do CSV...")

# Ler o CSV completo (agora contendo tudo)
df_final = pd.read_csv(ARQUIVO_SAIDA_CSV, sep=';', encoding='utf-8-sig')

# Tratamento para ler a lista de tags que foi salva como string
def parse_tags(tags_str):
    try:
        # Tenta carregar como JSON
        return json.loads(tags_str.replace("'", '"'))
    except:
        # Fallback se não for JSON válido (ex: erro na gravação anterior)
        return []

df_final['Tags_IA'] = df_final['Tags_IA'].apply(parse_tags)

# Explodir as tags para contagem (uma linha por tag)
df_tags = df_final.explode('Tags_IA')

# A. Contagem Geral
top_tags_geral = df_tags['Tags_IA'].value_counts().head(10)
top_cat_geral = df_final['Categoria_Bardin'].value_counts()

# B. Contagem por Indicador
tags_por_indicador = df_tags.groupby(['Indicador', 'Tags_IA']).size().reset_index(name='Qtd')
tags_por_indicador = tags_por_indicador.sort_values(['Indicador', 'Qtd'], ascending=[True, False])

# C. Contagem por Setor
tags_por_setor = df_tags.groupby(['Setor', 'Tags_IA']).size().reset_index(name='Qtd')
tags_por_setor = tags_por_setor.sort_values(['Setor', 'Qtd'], ascending=[True, False])

# Construção do Texto Final
output_text = []
output_text.append("="*60)
output_text.append("RELATÓRIO ANALÍTICO AUTOMATIZADO (MEC/INEP)")
output_text.append("="*60 + "\n")

output_text.append("--- ESTATÍSTICAS GERAIS ---")
output_text.append(f"Total de Avaliações: {len(df_final)}")
output_text.append("\nTOP 5 CATEGORIAS (BARDIN/IA):")
for cat, count in top_cat_geral.items():
    output_text.append(f"  - {cat}: {count}")

output_text.append("\nTOP 10 TAGS GERAIS:")
for tag, count in top_tags_geral.items():
    output_text.append(f"  - {tag}: {count}")

output_text.append("\n" + "="*60 + "\n")

output_text.append("--- TOP TAGS POR INDICADOR ---")
indicadores_unicos = tags_por_indicador['Indicador'].unique()
for ind in indicadores_unicos:
    output_text.append(f"\nINDICADOR {ind}:")
    subset = tags_por_indicador[tags_por_indicador['Indicador'] == ind].head(3) # Top 3 tags
    for _, row in subset.iterrows():
        output_text.append(f"  {row['Tags_IA']}: {row['Qtd']}")

output_text.append("\n" + "="*60 + "\n")

output_text.append("--- TOP TAGS POR SETOR ---")
setores_unicos = tags_por_setor['Setor'].unique()
for setor in setores_unicos:
    output_text.append(f"\nSETOR: {setor}")
    subset = tags_por_setor[tags_por_setor['Setor'] == setor].head(3)
    for _, row in subset.iterrows():
        output_text.append(f"  {row['Tags_IA']}: {row['Qtd']}")

output_text.append("\n" + "="*60 + "\n")
output_text.append("DETALHAMENTO DOS APONTAMENTOS\n")

# Adiciona o corpo do texto reformatado
for indicador, group in df_final.groupby('Indicador'):
    output_text.append(f"\n>>> INDICADOR: {indicador}")
    output_text.append("-" * 40)
    
    for _, row in group.iterrows():
        tags_str = ", ".join(row['Tags_IA'])
        output_text.append(f"LOCALIZAÇÃO: {row['Setor']}")
        output_text.append(f"CURSO: {row['Curso']} (Nota: {row['Nota']})")
        output_text.append(f"CATEGORIA: {row['Categoria_Bardin']}")
        output_text.append(f"PONTOS NEGATIVOS: {row['Pontos_Negativos']}")
        output_text.append(f"TAGS: {tags_str}")
        output_text.append(f"JUSTIFICATIVA: {str(row['Justificativa'])[:300]}...")
        output_text.append("-" * 20)

# Salvar Arquivo de Relatório
with open(ARQUIVO_SAIDA_TXT, "w", encoding="utf-8") as f:
    f.write("\n".join(output_text))

print(f"Processamento concluído! Arquivos '{ARQUIVO_SAIDA_TXT}' e '{ARQUIVO_SAIDA_CSV}' atualizados.")