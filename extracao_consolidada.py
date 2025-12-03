import re
import os
from pathlib import Path
import pandas as pd
import shutil
from pypdf import PdfReader
import concurrent.futures
from tqdm import tqdm

# Importações opcionais para OCR (só se necessário)
try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image
    import io
    
    # Aumenta o limite de pixels para evitar DecompressionBombWarning em PDFs grandes
    Image.MAX_IMAGE_PIXELS = None
    
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️  Bibliotecas de OCR não encontradas. OCR será desabilitado.")
    print("   Para habilitar OCR, instale: pip install PyMuPDF pytesseract Pillow")

# --- CONFIGURAÇÃO ---
INPUT_DIR = Path(__file__).parent
OUTPUT_STRUCTURED_CSV = 'relatorio_consolidado_extraido.json'
OUTPUT_JUSTIFICATIVAS_CSV = 'relatorio_justificativas.json'
OCR_CACHE_DIR = Path('ocr_cache')
CORRECT_DIR = INPUT_DIR / 'correto'
DEBUG_DIR = INPUT_DIR / 'debug_txt'

# OCR Settings
OCR_LANGUAGE = 'por'
MIN_TEXT_LENGTH = 100  # Mínimo de caracteres para considerar que PDF tem texto
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Processing
MAX_WORKERS = os.cpu_count()
# --- FIM DA CONFIGURAÇÃO ---

# Configura Tesseract se disponível
if OCR_AVAILABLE:
    try:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    except:
        pass

# --- CURSOS OFICIAIS DA UFPR ---
# Lista de cursos de graduação (nomes oficiais)
CURSOS_UFPR_OFICIAL = [
    # Curitiba
    'Administração',
    'Agronomia',
    'Arquitetura e Urbanismo',
    'Artes Visuais',
    'Biomedicina',
    'Ciências Biológicas',
    'Ciências da Computação',
    'Ciências Contábeis',
    'Ciências Econômicas',
    'Ciências Sociais',
    'Design Gráfico',
    'Design de Produto',
    'Direito',
    'Educação Física',
    'Enfermagem',
    'Engenharia Ambiental',
    'Engenharia de Bioprocessos e Biotecnologia',
    'Engenharia Cartográfica e de Agrimensura',
    'Engenharia Civil',
    'Engenharia Elétrica',
    'Engenharia Florestal',
    'Engenharia Industrial Madereira',
    'Engenharia Mecânica',
    'Engenharia de Produção',
    'Engenharia Química',
    'Estatística e Ciência de Dados',
    'Expressão Gráfica',
    'Farmácia',
    'Filosofia',
    'Física',
    'Fisioterapia',
    'Geografia',
    'Geologia',
    'Gestão da Informação',
    'História',
    'História Memória e Imagem',
    'Informática Biomédica',
    'Jornalismo',
    'Letras',
    'Letras Libras',
    'Matemática',
    'Matemática Industrial',
    'Medicina',
    'Medicina Veterinária',
    'Música',
    'Nutrição',
    'Odontologia',
    'Pedagogia',
    'Produção Cultural',
    'Psicologia',
    'Publicidade e Propaganda',
    'Química',
    'Relações Públicas',
    'Tecnologia em Análise e Desenvolvimento de Sistemas',
    'Tecnologia em Comunicação Institucional',
    'Tecnologia em Gestão Pública',
    'Tecnologia em Gestão da Qualidade',
    'Tecnologia em Luteria',
    'Tecnologia em Negócios Imobiliários',
    'Tecnologia em Produção Cênica',
    'Tecnologia em Secretariado',
    'Terapia Ocupacional',
    'Turismo',
    'Zootecnia',
    
    # Jandaia do Sul
    'Ciências Exatas',  # Licenciatura em Ciências Exatas (Química, Física ou Matemática)
    'Engenharia Agrícola',
    'Engenharia de Alimentos',
    'Inteligência Artificial e Engenharia de Software',
    
    # Matinhos (UFPR Litoral)
    'Administração Pública',
    'Artes',
    'Agroecologia',
    'Ciências',
    'Ciências Ambientais',
    'Educação do Campo',
    # 'Educação Física',  # Já existe em Curitiba
    # 'Geografia',  # Já existe em Curitiba
    'Gestão de Turismo',
    'Gestão e Empreendedorismo',
    'Gestão Imobiliária',
    'Linguagem e Comunicação',
    'Saúde Coletiva',
    'Serviço Social',
    
    # Palotina
    # 'Agronomia',  # Já existe em Curitiba
    # 'Ciências Biológicas',  # Já existe em Curitiba
    # 'Ciências Exatas',  # Já existe em Jandaia do Sul
    'Computação',
    'Engenharia de Aquicultura',
    # 'Engenharia de Bioprocessos e Biotecnologia',  # Já existe em Curitiba
    'Engenharia de Energias Renováveis',
    # 'Medicina Veterinária',  # Já existe em Curitiba
    
    # Pontal do Paraná (Centro de Estudos do Mar)
    # 'Ciências Exatas',  # Já existe em Jandaia do Sul
    'Engenharia Ambiental e Sanitária',  # Variação de Engenharia Ambiental
    # 'Engenharia Civil',  # Já existe em Curitiba
    # 'Engenharia de Aquicultura',  # Já existe em Palotina
    'Oceanografia'
]

# Cria um dicionário para normalização (todas as variações em UPPER → nome oficial)
CURSOS_NORMALIZACAO = {}
for curso in CURSOS_UFPR_OFICIAL:
    # Adiciona o nome oficial em upper

    CURSOS_NORMALIZACAO[curso.upper()] = curso
    # Adiciona variações sem acentos
    curso_sem_acento = (curso.upper()
                        .replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
                        .replace('Ó', 'O').replace('Ú', 'U').replace('Ã', 'A')
                        .replace('Õ', 'O').replace('Â', 'A').replace('Ê', 'E')
                        .replace('Ô', 'O').replace('Ç', 'C'))
    CURSOS_NORMALIZACAO[curso_sem_acento] = curso

# Adiciona variações comuns de nomenclatura
CURSOS_NORMALIZACAO.update({
    # Curitiba
    'CIENCIA DA COMPUTACAO': 'Ciências da Computação',
    'CIENCIAS DA COMPUTACAO': 'Ciências da Computação',
    'CIENCIA BIOLOGICA': 'Ciências Biológicas',
    'CIENCIAS BIOLOGICAS': 'Ciências Biológicas',
    'CIENCIA CONTABIL': 'Ciências Contábeis',
    'CIENCIAS CONTABEIS': 'Ciências Contábeis',
    'CIENCIA ECONOMICA': 'Ciências Econômicas',
    'CIENCIAS ECONOMICAS': 'Ciências Econômicas',
    'CIENCIA SOCIAL': 'Ciências Sociais',
    'DESIGN GRAFICO': 'Design Gráfico',
    'EDUCACAO FISICA': 'Educação Física',
    'ENGENHARIA ELETRICA': 'Engenharia Elétrica',
    'ESTATISTICA E CIENCIA DE DADOS': 'Estatística e Ciência de Dados',
    'EXPRESSAO GRAFICA': 'Expressão Gráfica',
    'FARMACIA': 'Farmácia',
    'FISICA': 'Física',
    'HISTORIA': 'História',
    'HISTORIA MEMORIA E IMAGEM': 'História Memória e Imagem',
    'INFORMATICA BIOMEDICA': 'Informática Biomédica',
    'MATEMATICA': 'Matemática',
    'MATEMATICA INDUSTRIAL': 'Matemática Industrial',
    'MEDICINA VETERINARIA': 'Medicina Veterinária',
    'MUSICA': 'Música',
    'NUTRICAO': 'Nutrição',
    'QUIMICA': 'Química',
    'RELACOES PUBLICAS': 'Relações Públicas',
    'TERAPIA OCUPACIONAL': 'Terapia Ocupacional',
    'ANALISE E DESENVOLVIMENTO DE SISTEMAS': 'Tecnologia em Análise e Desenvolvimento de Sistemas',
    'COMUNICACAO INSTITUCIONAL': 'Tecnologia em Comunicação Institucional',
    'GESTAO PUBLICA': 'Tecnologia em Gestão Pública',
    'GESTAO DA QUALIDADE': 'Tecnologia em Gestão da Qualidade',
    'LUTERIA': 'Tecnologia em Luteria',
    'NEGOCIOS IMOBILIARIOS': 'Tecnologia em Negócios Imobiliários',
    'PRODUCAO CENICA': 'Tecnologia em Produção Cênica',
    'SECRETARIADO': 'Tecnologia em Secretariado',
    
    # Jandaia do Sul
    'CIENCIAS EXATAS': 'Ciências Exatas',
    'LICENCIATURA EM CIENCIAS EXATAS': 'Ciências Exatas',
    'LICENCIATURA CIENCIAS EXATAS': 'Ciências Exatas',
    'CIENCIAS EXATAS - QUIMICA, FISICA OU MATEMATICA': 'Ciências Exatas',
    'CIENCIAS EXATAS QUIMICA FISICA OU MATEMATICA': 'Ciências Exatas',
    'ENGENHARIA AGRICOLA': 'Engenharia Agrícola',
    'ENGENHARIA DE ALIMENTOS': 'Engenharia de Alimentos',
    'INTELIGENCIA ARTIFICIAL E ENGENHARIA DE SOFTWARE': 'Inteligência Artificial e Engenharia de Software',
    'INTELIGENCIA ARTIFICIAL': 'Inteligência Artificial e Engenharia de Software',
    'ENGENHARIA DE SOFTWARE': 'Inteligência Artificial e Engenharia de Software',
    'IA E ENGENHARIA DE SOFTWARE': 'Inteligência Artificial e Engenharia de Software',
    
    # Matinhos (UFPR Litoral)
    'ADMINISTRACAO PUBLICA': 'Administração Pública',
    'ADMINISTRACAO PUBLICA': 'Administração Pública',
    'AGROECOLOGIA': 'Agroecologia',
    'CIENCIAS AMBIENTAIS': 'Ciências Ambientais',
    'CIENCIA AMBIENTAL': 'Ciências Ambientais',
    'EDUCACAO DO CAMPO': 'Educação do Campo',
    'GESTAO DE TURISMO': 'Gestão de Turismo',
    'GESTAO DO TURISMO': 'Gestão de Turismo',
    'GESTAO E EMPREENDEDORISMO': 'Gestão e Empreendedorismo',
    'GESTAO IMOBILIARIA': 'Gestão Imobiliária',
    'GESTAO IMOBILIARIA': 'Gestão Imobiliária',
    'LINGUAGEM E COMUNICACAO': 'Linguagem e Comunicação',
    'SAUDE COLETIVA': 'Saúde Coletiva',
    'SERVICO SOCIAL': 'Serviço Social',
    
    # Palotina
    'COMPUTACAO': 'Computação',
    'ENGENHARIA DE AQUICULTURA': 'Engenharia de Aquicultura',
    'AQUICULTURA': 'Engenharia de Aquicultura',
    'ENGENHARIA DE ENERGIAS RENOVAVEIS': 'Engenharia de Energias Renováveis',
    'ENGENHARIA DE ENERGIAS RENOVAVEIS': 'Engenharia de Energias Renováveis',
    'ENERGIAS RENOVAVEIS': 'Engenharia de Energias Renováveis',
    
    # Pontal do Paraná (Centro de Estudos do Mar)
    'ENGENHARIA AMBIENTAL E SANITARIA': 'Engenharia Ambiental e Sanitária',
    'ENGENHARIA AMBIENTAL E SANITARIA': 'Engenharia Ambiental e Sanitária',
    'AMBIENTAL E SANITARIA': 'Engenharia Ambiental e Sanitária',
    'OCEANOGRAFIA': 'Oceanografia',
})



# --- PADRÕES DE REGEX ---
# Para dados estruturados - Padrões MUITO mais estritos

# Nome do curso - Múltiplos padrões
# Padrão 1: Do cabeçalho estruturado "Curso(s) / Habilitação(ões) sendo avaliado(s):"
NOME_CURSO_HEADER_PATTERN = re.compile(
    r"Curso\(s\)\s*/\s*Habilitação\(ões\)\s+sendo\s+avaliado\(s\)[:\s]+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç\s-]+?)\s*(?:Informações|$)",
    re.IGNORECASE
)
# Padrão 2: Do corpo do documento
NOME_CURSO_PATTERN = re.compile(
    r"Curso\(s\)\s*/\s*Habilitação\(ões\)[^:]*?:\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç\s-]+?)\s*;\s*Grau",
    re.IGNORECASE
)

# Código MEC - Múltiplos padrões
# Padrão 1: "Código MEC:"
CODIGO_MEC_HEADER_PATTERN = re.compile(r"Código\s+MEC[:\s]+(\d{6,8})", re.IGNORECASE)
# Padrão 2: "Código do Curso" ou "Código e-MEC do Curso"
CODIGO_MEC_PATTERN = re.compile(r"Código\s+(?:e-MEC\s+)?do\s+Curso[:\s]+(\d{6,8})", re.IGNORECASE)

# Ano de avaliação - Múltiplos padrões
# Padrão 1: "Período de Visita: DD/MM/AAAA"
ANO_VISITA_PATTERN = re.compile(
    r"Período\s+de\s+Visita[:\s]+\d{1,2}/\d{1,2}/(20\d{2})",
    re.IGNORECASE
)
# Padrão 2: "ocorreu no período"
ANO_AVALIACAO_PATTERN = re.compile(
    r"ocorreu\s+no\s+per[íi]odo.*?(20\d{2})",
    re.IGNORECASE | re.DOTALL
)

# Cidade - Extrai após CEP no formato "Cidade - UF"
CIDADE_PATTERN = re.compile(
    r"CEP[:\s-]*(\d[\d.-]+).*?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+[a-záéíóúâêôãõç]+)?)[\s-]+[A-Z]{2}\.",
    re.IGNORECASE | re.DOTALL
)

# Campus - Múltiplos padrões
# Padrão 1: Do endereço (ex: "campus centro")
CAMPUS_HEADER_PATTERN = re.compile(
    r"\d+\s*-\s*campus\s+([a-záéíóúâêôãõç\s]+?)\s*-",
    re.IGNORECASE
)
# Padrão 2 : Do texto "Campus X, situado"
CAMPUS_PATTERN = re.compile(
    r"Campus\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){0,3}),\s*situado",
    re.IGNORECASE
)

# Modalidade - APENAS após Grau:
MODALIDADE_PATTERN = re.compile(
    r"Grau:\s*(Licenciatura|Bacharelado|Tecnólogo)",
    re.IGNORECASE
)

# Padrões para conceitos
CONCEITOS_PATTERN = re.compile(
    r"CONCEITO\s+FINAL\s+CONTÍNUO\s+CONCEITO\s+FINAL\s+FAIXA\s*([\d,.]+)\s+([\d,.]+)",
    re.IGNORECASE | re.DOTALL
)

# Padrão para indicadores
INDICADORES_PATTERN = re.compile(
    r"^\s*(\d+\.\d+)\..*?Justificativa para conceito\s*(.*?)\s*:",
    re.MULTILINE | re.DOTALL | re.IGNORECASE
)

# Padrão para dimensões (notas globais das 3 dimensões)
# Captura apenas valores no formato X,XX ou X.XX (entre 1-5)
DIMENSOES_PATTERN = re.compile(
    r"Dimensão\s+(\d):\s*[^\d]*?([1-5][\.,]\d{1,2}|[1-5])",
    re.IGNORECASE
)

# Mapeamento Campus → Cidade (oficial UFPR)
CAMPUS_CIDADE_MAP = {
    # Curitiba
    'Prédio Histórico': 'Curitiba',
    'Reitoria': 'Curitiba',
    'Rebouças': 'Curitiba',
    'Batel': 'Curitiba',
    'Juvevê': 'Curitiba',
    'Cabral': 'Curitiba',
    'Jardim Botânico': 'Curitiba',
    'Centro Politécnico': 'Curitiba',
    'Complexo Hospital de Clínicas': 'Curitiba',
    'Setor de Educação Profissional e Tecnológica (SEPT)': 'Curitiba',
    
    # Pontal do Paraná
    'Centro de Estudos do Mar': 'Pontal do Paraná',
    
    # Matinhos
    'UFPR Litoral': 'Matinhos',
    
    # Palotina
    'Campus Palotina': 'Palotina',
    
    # Jandaia do Sul
    'Campus Avançado Jandaia do Sul': 'Jandaia do Sul',
    
    # Toledo
    'Campus Toledo': 'Toledo'
}

# Mapeamento de campus da UFPR (para normalização de texto extraído → nome oficial)
CAMPUS_UFPR = {
    # Curitiba
    'PRÉDIO HISTÓRICO': 'Prédio Histórico',
    'PREDIO HISTORICO': 'Prédio Histórico',
    'HISTÓRICO': 'Prédio Histórico',
    'HISTORICO': 'Prédio Histórico',
    'REITORIA': 'Reitoria',
    'REBOUÇAS': 'Rebouças',
    'REBOUCAS': 'Rebouças',
    'BATEL': 'Batel',
    'JUVEVÊ': 'Juvevê',
    'JUVEVE': 'Juvevê',
    'CABRAL': 'Cabral',
    'JARDIM BOTÂNICO': 'Jardim Botânico',
    'JARDIM BOTANICO': 'Jardim Botânico',
    'CENTRO POLITÉCNICO': 'Centro Politécnico',
    'CENTRO POLITECNICO': 'Centro Politécnico',
    'POLITÉCNICO': 'Centro Politécnico',
    'POLITECNICO': 'Centro Politécnico',
    'HOSPITAL DE CLÍNICAS': 'Complexo Hospital de Clínicas',
    'HOSPITAL DE CLINICAS': 'Complexo Hospital de Clínicas',
    'COMPLEXO HOSPITAL DE CLÍNICAS': 'Complexo Hospital de Clínicas',
    'COMPLEXO HOSPITAL DE CLINICAS': 'Complexo Hospital de Clínicas',
    'HC': 'Complexo Hospital de Clínicas',
    'SEPT': 'Setor de Educação Profissional e Tecnológica (SEPT)',
    'SETOR DE EDUCAÇÃO PROFISSIONAL E TECNOLÓGICA': 'Setor de Educação Profissional e Tecnológica (SEPT)',
    'SETOR DE EDUCACAO PROFISSIONAL E TECNOLOGICA': 'Setor de Educação Profissional e Tecnológica (SEPT)',
    
    # Pontal do Paraná
    'PONTAL DO PARANÁ': 'Centro de Estudos do Mar',
    'PONTAL DO PARANA': 'Centro de Estudos do Mar',
    'PONTAL': 'Centro de Estudos do Mar',
    'CENTRO DE ESTUDOS DO MAR': 'Centro de Estudos do Mar',
    'CEM': 'Centro de Estudos do Mar',
    
    # Matinhos
    'MATINHOS': 'UFPR Litoral',
    'LITORAL': 'UFPR Litoral',
    'UFPR LITORAL': 'UFPR Litoral',
    
    # Palotina
    'PALOTINA': 'Campus Palotina',
    'CAMPUS PALOTINA': 'Campus Palotina',
    
    # Jandaia do Sul
    'JANDAIA DO SUL': 'Campus Avançado Jandaia do Sul',
    'JANDAIA': 'Campus Avançado Jandaia do Sul',
    'CAMPUS AVANÇADO JANDAIA DO SUL': 'Campus Avançado Jandaia do Sul',
    'CAMPUS AVANCADO JANDAIA DO SUL': 'Campus Avançado Jandaia do Sul',
    
    # Toledo
    'TOLEDO': 'Campus Toledo',
    'CAMPUS TOLEDO': 'Campus Toledo'
}

def normalizar_campus(campus_extraido):
    """
    Normaliza o nome do campus extraído para o nome oficial da UFPR.
    """
    if not campus_extraido:
        return ''
    
    campus_upper = campus_extraido.strip().upper()
    
    # Busca exata no mapeamento
    if campus_upper in CAMPUS_UFPR:
        return CAMPUS_UFPR[campus_upper]
    
    # Busca parcial (contém)
    for chave, valor in CAMPUS_UFPR.items():
        if chave in campus_upper or campus_upper in chave:
            return valor
    
    # Se não encontrou, retorna o original
    return campus_extraido.strip()


def normalizar_cidade(cidade_extraida):
    """
    Normaliza o nome da cidade extraída.
    """
    if not cidade_extraida:
        return ''
    
    # Capitaliza corretamente
    cidade = cidade_extraida.strip().title()
    return cidade


def normalizar_modalidade(modalidade_extraida):
    """
    Normaliza a modalidade do curso.
    """
    if not modalidade_extraida:
        return ''
    
    modalidade_map = {
        'LICENCIATURA': 'Licenciatura',
        'BACHARELADO': 'Bacharelado',
        'TECNÓLOGO': 'Tecnólogo',
        'TECNOLOGO': 'Tecnólogo'
    }
    
    modalidade_upper = modalidade_extraida.strip().upper()
    return modalidade_map.get(modalidade_upper, modalidade_extraida.strip())


def formatar_decimal(valor):
    """
    Converte um valor para float.
    Retorna float, 'NSA' ou None se não for válido.
    """
    if not valor:
        return None
    
    valor_str = str(valor).strip().upper()
    
    # Se for NSA, mantém como está
    if valor_str == 'NSA':
        return 'NSA'
    
    try:
        # Remove vírgulas e converte para float
        return float(valor_str.replace(',', '.'))
    except (ValueError, TypeError):
        # Se não for possível converter, retorna None
        return None


def formatar_inteiro(valor):
    """
    Converte um valor para int.
    Retorna int, 'NSA' ou None se não for válido.
    """
    if not valor:
        return None
    
    valor_str = str(valor).strip().upper()
    
    # Se for NSA, mantém como está
    if valor_str == 'NSA':
        return 'NSA'
    
    try:
        # Remove vírgulas e converte para float antes de int (para lidar com "2019.0")
        return int(float(valor_str.replace(',', '.')))
    except (ValueError, TypeError):
        # Se não for possível converter, retorna None
        return None


def normalizar_curso(curso_extraido):
    """
    Normaliza o nome do curso extraído para o nome oficial da UFPR.
    Retorna o nome oficial se encontrado, ou o nome original se não encontrar.
    """
    if not curso_extraido:
        return ''
    
    curso_upper = curso_extraido.strip().upper()
    
    # Remove prefixos de modalidade que podem ter sido capturados
    curso_upper = re.sub(r'^(BACHARELADO|LICENCIATURA|TECNÓLOGO|TECNOLOGO)\s+(EM\s+)?', '', curso_upper)
    
    # Busca exata no dicionário de normalização
    if curso_upper in CURSOS_NORMALIZACAO:
        return CURSOS_NORMALIZACAO[curso_upper]
    
    # Busca parcial - verifica se algum curso conhecido está contido no texto extraído
    for variacao, curso_oficial in CURSOS_NORMALIZACAO.items():
        if variacao in curso_upper or curso_upper in variacao:
            # Verifica se a similaridade é alta o suficiente
            if len(curso_upper) >= 5 and len(variacao) >= 5:
                return curso_oficial
    
    # Se não encontrou correspondência, retorna o original (title case)
    return curso_extraido.strip().title()


# --- FIM DOS PADRÕES ---


def verificar_texto_pdf(pdf_path: Path) -> bool:
    """
    Verifica se o PDF tem texto extraível suficiente.
    Retorna True se tiver texto, False caso contrário.
    """
    try:
        reader = PdfReader(pdf_path)
        # Verifica as primeiras 3 páginas
        texto_total = ""
        for i, page in enumerate(reader.pages[:3]):
            texto_total += page.extract_text() or ""
            if len(texto_total) > MIN_TEXT_LENGTH:
                return True
        
        return len(texto_total.strip()) > MIN_TEXT_LENGTH
    except Exception as e:
        print(f"❌ Erro ao verificar texto em '{pdf_path.name}': {e}")
        return False


def aplicar_ocr_pdf(pdf_path: Path) -> Path:
    """
    Aplica OCR a um PDF e salva a versão com OCR no cache.
    Retorna o caminho do PDF com OCR.
    """
    if not OCR_AVAILABLE:
        raise RuntimeError("OCR não está disponível. Instale as bibliotecas necessárias.")
    
    # Cria diretório de cache se não existir
    OCR_CACHE_DIR.mkdir(exist_ok=True)
    
    output_pdf_path = OCR_CACHE_DIR / pdf_path.name
    
    # Se já foi processado, retorna o cache
    if output_pdf_path.exists():
        print(f"  ♻️  Usando PDF com OCR do cache: {pdf_path.name}")
        return output_pdf_path
    
    print(f"  🔍 Aplicando OCR em: {pdf_path.name}")
    
    try:
        doc = fitz.open(pdf_path)
        output_pdf = fitz.open()
        
        for i, page in enumerate(doc):
            # Tenta renderizar com diferentes DPIs para evitar erro de memória
            dpis_to_try = [300, 150, 72]
            pix = None
            
            for dpi in dpis_to_try:
                try:
                    pix = page.get_pixmap(dpi=dpi)
                    break # Sucesso
                except RuntimeError as e:
                    print(f"  [!] Erro de memória com DPI {dpi} na pág {i+1}. Tentando menor...")
                    if dpi == dpis_to_try[-1]:
                        raise e # Se falhar no menor, relança
            
            if not pix:
                continue
                
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            print(f"    ... OCR na página {i+1}/{len(doc)} (DPI: {dpi})")
            
            # Aplica OCR com timeout de 2 minutos por página
            try:
                pagina_com_ocr_bytes = pytesseract.image_to_pdf_or_hocr(
                    img, lang=OCR_LANGUAGE, extension='pdf', timeout=120
                )
                
                pagina_com_ocr = fitz.open("pdf", pagina_com_ocr_bytes)
                output_pdf.insert_pdf(pagina_com_ocr)
            except RuntimeError as e:
                print(f"    [!] Timeout ou erro no Tesseract na página {i+1}: {e}")
                # Opcional: Adicionar a página original sem OCR se falhar?
                # Por enquanto, apenas pula a página problemática para não travar tudo
                continue
        
        output_pdf.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        output_pdf.close()
        doc.close()
        
        print(f"  ✅ OCR concluído: {output_pdf_path.name}")
        return output_pdf_path
        
    except Exception as e:
        # Se houver erro fatal no OCR, retorna o original para não parar o fluxo, mas avisa
        print(f"❌ Erro crítico no OCR de '{pdf_path.name}': {e}")
        return pdf_path


def extrair_texto_pdf(pdf_path: Path, usar_ocr: bool = False) -> str:
    """
    Extrai texto de um PDF.
    Se usar_ocr=True, aplica OCR primeiro.
    """
    try:
        if usar_ocr:
            pdf_path = aplicar_ocr_pdf(pdf_path)
        
        reader = PdfReader(pdf_path)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text() or ""
            texto_completo += "\n"
        
        return texto_completo
        
    except Exception as e:
        print(f"❌ Erro ao extrair texto de '{pdf_path.name}': {e}")
        return ""


def extrair_dados_estruturados(texto: str, pdf_path: Path) -> dict:
    """
    Extrai dados estruturados do texto (curso, indicadores, conceitos).
    """
    dados = {}
    
    # Limpeza básica: normaliza espaços
    texto_limpo = re.sub(r'\s+', ' ', texto).strip()
    
    # --- Extração do Curso e Código ---
    # TENTA o padrão do cabeçalho PRIMEIRO
    nome_curso_match = NOME_CURSO_HEADER_PATTERN.search(texto_limpo)
    if not nome_curso_match:
        # Se não encontrou, tenta o padrão do corpo do documento
        nome_curso_match = NOME_CURSO_PATTERN.search(texto_limpo)
    
    if nome_curso_match:
        nome_curso = nome_curso_match.group(1).strip()
        
        # Validação RIGOROSA - verifica palavras inválidas
        palavras_invalidas = ['informações', 'comissão', 'avaliação', 'regulação', 'docentes', 
                               'categorias', 'processo seletivo', 'vestibular', 'prof', 'dra', 
                               'questões', 'atendimento', 'regime', 'lei', 'decreto', 'ciências jurídicas']
        
        # Verifica se é um nome válido (não é só números nem contém palavras inválidas)
        if (len(nome_curso) <= 80 and len(nome_curso) >= 3 and 
            not nome_curso.isdigit() and 
            not any(inv in nome_curso.lower() for inv in palavras_invalidas) and
            re.search(r'[A-ZÁÉÍÓÚÂÊÔÃÕÇ]', nome_curso)):  # Deve ter pelo menos uma letra maiúscula
            
            # Normaliza o nome do curso usando a lista oficial
            curso_normalizado = normalizar_curso(nome_curso)
            dados['Curso'] = curso_normalizado
        else:
            dados['Curso'] = None
    else:
        dados['Curso'] = None
    
    # Código MEC: tenta padrão do header primeiro
    codigo_match = CODIGO_MEC_HEADER_PATTERN.search(texto_limpo)
    if not codigo_match:
        codigo_match = CODIGO_MEC_PATTERN.search(texto_limpo)
    
    dados['Id_MEC'] = formatar_inteiro(codigo_match.group(1).strip()) if codigo_match else None
    
    # --- Extração de Ano, Cidade, Campus, Modalidade ---
    # Ano de avaliação: tenta padrão de visita primeiro
    ano_match = ANO_VISITA_PATTERN.search(texto_limpo)
    if not ano_match:
        ano_match = ANO_AVALIACAO_PATTERN.search(texto_limpo)
    
    if ano_match:
        ano = ano_match.group(1).strip()
        # Valida que é um ano entre 2000-2099
        if ano.isdigit() and 2000 <= int(ano) <= 2099:
            dados['Ano_avaliacao'] = formatar_inteiro(ano)
        else:
            dados['Ano_avaliacao'] = None
    else:
        dados['Ano_avaliacao'] = None
    
    # Campus: tenta padrão do header primeiro
    campus_match = CAMPUS_HEADER_PATTERN.search(texto_limpo)
    if not campus_match:
        campus_match = CAMPUS_PATTERN.search(texto_limpo)
    
    if campus_match:
        campus_bruto = campus_match.group(1).strip()
        # Normaliza usando a lista válida (já valida automaticamente)
        campus_normalizado = normalizar_campus(campus_bruto)
        dados['Campus'] = campus_normalizado
        
        # Preenche a Cidade automaticamente baseado no Campus normalizado
        dados['Cidade'] = CAMPUS_CIDADE_MAP.get(campus_normalizado, None)
    else:
        dados['Campus'] = None
        # Se não encontrou campus, tenta extrair cidade diretamente do texto
        cidade_match = CIDADE_PATTERN.search(texto_limpo)
        if cidade_match:
            cidade_bruta = cidade_match.group(2).strip()  # Grupo 2 é a cidade
            # Remove preposições comuns
            cidade_bruta = re.sub(r'^(de|da|do|dos|das)\s+', '', cidade_bruta, flags=re.IGNORECASE)
            dados['Cidade'] = cidade_bruta.strip().title()
        else:
            dados['Cidade'] = None
    
    # Modalidade - extrai e normaliza
    modalidade_match = MODALIDADE_PATTERN.search(texto_limpo)
    if modalidade_match:
        modalidade_bruta = modalidade_match.group(1)
        # Normaliza usando a lista válida
        dados['Modalidade'] = normalizar_modalidade(modalidade_bruta)
    else:
        dados['Modalidade'] = None

    
    # --- Extração de Dimensões e Indicadores (Valores Relacionados) ---
    
    # 1. Inicialização
    # Dimensões
    dados['1'] = None
    dados['2'] = None
    dados['3'] = None
    
    # Indicadores
    indicadores_esperados = []
    indicadores_esperados.extend([f"1.{i}" for i in range(1, 25)]) # Dimensão 1
    indicadores_esperados.extend([f"2.{i}" for i in range(1, 17)]) # Dimensão 2
    indicadores_esperados.extend([f"3.{i}" for i in range(1, 18)]) # Dimensão 3
    
    for ind in indicadores_esperados:
        dados[ind] = None

    # 2. Extração de Dimensões
    dimensoes_matches = DIMENSOES_PATTERN.findall(texto_limpo)
    for num_dim, nota_dim in dimensoes_matches:
        valor_formatado = formatar_decimal(nota_dim)
        if valor_formatado is not None and valor_formatado != 'NSA':
            if 1.0 <= valor_formatado <= 5.0:
                dados[num_dim] = valor_formatado
            else:
                print(f"  ⚠️  Valor inválido para dimensão {num_dim}: {valor_formatado} (esperado: 1-5)")
        else:
            dados[num_dim] = valor_formatado

    # 3. Extração de Indicadores
    matches = INDICADORES_PATTERN.findall(texto)
    for indicador, nota in matches:
        if indicador in indicadores_esperados:
            dados[indicador] = formatar_decimal(nota)
    
    # --- Extração de Conceitos ---
    conceitos_match = CONCEITOS_PATTERN.search(texto_limpo)
    if conceitos_match:
        dados['CONCEITO FINAL CONTÍNUO'] = formatar_decimal(conceitos_match.group(1).strip())
        dados['CONCEITO FINAL FAIXA'] = formatar_inteiro(conceitos_match.group(2).strip())
    else:
        dados['CONCEITO FINAL CONTÍNUO'] = None
        dados['CONCEITO FINAL FAIXA'] = None
    
    return dados


def extrair_justificativas(texto: str, curso_id: str) -> list:
    """
    Extrai justificativas de indicadores do texto.
    Retorna lista de dicts com CURSO, INDICADOR, JUSTIFICATIVA.
    """
    lista_justificativas = []
    
    # Divide o texto em blocos por indicador
    blocos = re.split(r'(?=^\s*\d+\.\d+\.)', texto, flags=re.MULTILINE)
    
    for bloco in blocos:
        # Extrai número do indicador
        indicador_match = re.match(r'^\s*(\d+\.\d+)\.', bloco)
        if not indicador_match:
            continue
        
        indicador_num = indicador_match.group(1)
        
        # Extrai justificativa
        justificativa_match = re.search(
            r"Justificativa para conceito.*?:(.*?)(?=\Z)",
            bloco, re.IGNORECASE | re.DOTALL
        )
        
        if justificativa_match:
            justificativa_texto = ' '.join(justificativa_match.group(1).split())
            
            lista_justificativas.append({
                'ID_DOCUMENTO': curso_id,  # Agora recebe o ID_DOCUMENTO (nome do arquivo)
                'INDICADOR': indicador_num,
                'JUSTIFICATIVA': justificativa_texto
            })
    
    return lista_justificativas


def processar_um_pdf(pdf_path: Path) -> tuple:
    """
    Processa um único PDF.
    Retorna tupla: (dados_estruturados, lista_justificativas)
    """
    print(f"\n[>] Processando: {pdf_path.name}")
    
    # Verifica se tem texto nativo
    tem_texto = verificar_texto_pdf(pdf_path)
    
    usar_ocr = False
    if not tem_texto:
        if OCR_AVAILABLE:
            print(f"  [!] PDF sem texto detectado. Usando OCR.")
            usar_ocr = True
        else:
            print(f"  [X] PDF sem texto e OCR não disponível. Pulando arquivo.")
            return None, None
    else:
        print(f"  [i] PDF com texto detectado. Usando extração nativa.")
    
    # Extrai texto (Nativo ou OCR)
    texto = extrair_texto_pdf(pdf_path, usar_ocr=usar_ocr)
    
    # Salva o texto extraído para debug
    try:
        debug_file = DEBUG_DIR / f"{pdf_path.stem}.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(texto if texto else "")
    except Exception as e:
        print(f"  [!] Erro ao salvar txt de debug: {e}")
    
    if not texto:
        print(f"  [X] Falha na extração de texto.")
        return None, None
        
    # Extração de dados estruturados
    dados = extrair_dados_estruturados(texto, pdf_path)
    
    # Adiciona ID único baseado no nome do arquivo para relacionamento
    id_documento = pdf_path.name
    dados['ID_DOCUMENTO'] = id_documento
    
    # Extração de justificativas (usando ID_DOCUMENTO como chave estrangeira)
    justificativas = extrair_justificativas(texto, id_documento)
    
    # Enriquece justificativas com dados do curso para facilitar relacionamento
    for just in justificativas:
        just['Curso'] = dados.get('Curso')
        just['Id_MEC'] = dados.get('Id_MEC')
    
    # Critério de sucesso: Todos os campos principais foram extraídos
    campos_obrigatorios = ['Curso', 'Id_MEC', 'Ano_avaliacao', 'Modalidade', 'Cidade', 'Campus']
    dados_completos = all(dados.get(campo) is not None for campo in campos_obrigatorios)
    
    if dados_completos:
        print(f"  [OK] Sucesso (Todos os campos principais extraídos)")
        print(f"  [OK] Extraído: {len(justificativas)} justificativas")
        
        # Move arquivo para pasta de corretos
        try:
            shutil.move(str(pdf_path), str(CORRECT_DIR / pdf_path.name))
            print(f"  [->] Arquivo movido para: {CORRECT_DIR.name}")
        except Exception as e:
            print(f"  [!] Erro ao mover arquivo: {e}")
            
        return dados, justificativas
    else:
        campos_faltantes = [campo for campo in campos_obrigatorios if dados.get(campo) is None]
        print(f"  [!] Dados incompletos. Faltando: {campos_faltantes}")
        return dados, justificativas


def processar_todos_pdfs():
    """
    Processa todos os PDFs e gera os CSVs.
    """
    pdf_files = list(INPUT_DIR.glob('*.pdf'))
    
    if not pdf_files:
        print(f"[X] Nenhum PDF encontrado em '{INPUT_DIR.resolve()}'")
        return
    
    # Cria diretório de corretos se não existir
    CORRECT_DIR.mkdir(exist_ok=True)
    # Cria diretório de debug se não existir
    DEBUG_DIR.mkdir(exist_ok=True)
    
    print(f"\n[*] Encontrados {len(pdf_files)} PDFs para processar")
    print(f"[*] Usando até {MAX_WORKERS} processos paralelos\n")
    
    # Listas para armazenar resultados
    lista_dados_estruturados = []
    lista_justificativas_completa = []
    
    # Processamento paralelo
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        resultados = list(tqdm(
            executor.map(processar_um_pdf, pdf_files),
            total=len(pdf_files),
            desc="[*] Progresso",
            unit="PDF"
        ))
    
    # Consolida resultados
    for dados, justificativas in resultados:
        if dados:
            lista_dados_estruturados.append(dados)
        if justificativas:
            lista_justificativas_completa.extend(justificativas)
    
    # Gera CSV de dados estruturados
    if lista_dados_estruturados:
        df_estruturados = pd.DataFrame(lista_dados_estruturados)
        
        # Define ordem das colunas
        fixed_cols_start = ['ID_DOCUMENTO', 'Curso', 'Id_MEC', 'Ano_avaliacao', 'Modalidade', 'Cidade', 'Campus']
        ind_1 = [f'1.{i}' for i in range(1, 25)]
        ind_2 = [f'2.{i}' for i in range(1, 17)]
        ind_3 = [f'3.{i}' for i in range(1, 18)]
        dimensoes = ['1', '2', '3']  # Notas das dimensões
        fixed_cols_end = ['CONCEITO FINAL CONTÍNUO', 'CONCEITO FINAL FAIXA']
        
        all_cols = fixed_cols_start + ind_1 + ind_2 + ind_3 + dimensoes + fixed_cols_end
        
        # Garante que colunas inteiras não sejam convertidas para float (devido a NaNs)
        cols_inteiras = ['Id_MEC', 'Ano_avaliacao', 'CONCEITO FINAL FAIXA']
        for col in cols_inteiras:
            if col in df_estruturados.columns:
                df_estruturados[col] = df_estruturados[col].astype(object).where(df_estruturados[col].notnull(), None)
        
        for col in all_cols:
            if col not in df_estruturados.columns:
                df_estruturados[col] = None
        
        df_estruturados = df_estruturados.reindex(columns=all_cols)
        df_estruturados.to_json(OUTPUT_STRUCTURED_CSV, orient='records', force_ascii=False, indent=2)
        
        print(f"\n[OK] Dados estruturados salvos: '{OUTPUT_STRUCTURED_CSV}'")
        print(f"   [*] {len(df_estruturados)} cursos processados")
    else:
        print("\n[!] Nenhum dado estruturado extraído")
    
    # Gera CSV de justificativas
    if lista_justificativas_completa:
        df_justificativas = pd.DataFrame(lista_justificativas_completa)
        
        # Reordena colunas para ficar mais organizado
        cols_order = ['ID_DOCUMENTO', 'Curso', 'Id_MEC', 'INDICADOR', 'JUSTIFICATIVA']
        # Garante que todas as colunas existam
        for col in cols_order:
            if col not in df_justificativas.columns:
                df_justificativas[col] = None
                
        df_justificativas = df_justificativas.reindex(columns=cols_order)
        
        df_justificativas.to_json(OUTPUT_JUSTIFICATIVAS_CSV, orient='records', force_ascii=False, indent=2)
        
        print(f"[OK] Justificativas salvas: '{OUTPUT_JUSTIFICATIVAS_CSV}'")
        print(f"   [*] {len(df_justificativas)} justificativas extraídas")
    else:
        print("\n[!] Nenhuma justificativa extraída")
    
    print("\n[*] Processamento concluído!")


if __name__ == '__main__':
    processar_todos_pdfs()
