# processar_pdfs.py
import os
from pathlib import Path
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import concurrent.futures

# --- CONFIGURAÇÃO ---
# Se você estiver no Windows, descomente e ajuste o caminho abaixo
# para onde você instalou o Tesseract.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Define o caminho do Tesseract para ambientes Linux como o Colab
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


# Idioma para o OCR. 'por' é para português.
# Para outros idiomas: https://tesseract-ocr.github.io/tessdoc/Data-Files-in-v4.00-(November-29,-2016).html
LANGUAGE = 'por'

# Pasta de entrada (onde estão os PDFs originais)
# Path('.') significa a pasta atual onde o script está rodando.
INPUT_DIR = Path('.')

# Pasta de saída para os PDFs com OCR
OUTPUT_DIR = Path('ocr')
# --- FIM DA CONFIGURAÇÃO ---

def processar_um_pdf(pdf_path):
    """Aplica OCR a um único arquivo PDF."""
    print(f"Processando: {pdf_path.name}...")
    try:
        # Define o caminho de saída para o novo PDF
        output_pdf_path = OUTPUT_DIR / pdf_path.name

        # Abre o PDF original com PyMuPDF
        doc = fitz.open(pdf_path)
        
        # Cria um novo PDF vazio para o resultado
        output_pdf = fitz.open()

        # Aplica OCR em cada página
        for i, page in enumerate(doc):
            print(f"  - Processando página {i+1}/{len(doc)} de {pdf_path.name}")
            
            # Renderiza a página como uma imagem de alta qualidade
            pix = page.get_pixmap(dpi=300)
            
            # Converte os bytes da imagem para um objeto de imagem PIL
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            # Usa Tesseract para criar uma página de PDF com o texto sobre a imagem
            pagina_com_ocr_bytes = pytesseract.image_to_pdf_or_hocr(
                img, lang=LANGUAGE, extension='pdf'
            )
            
            # Abre a página de PDF criada pelo Tesseract
            pagina_com_ocr = fitz.open("pdf", pagina_com_ocr_bytes)
            
            # Adiciona a página com OCR ao novo PDF de saída
            output_pdf.insert_pdf(pagina_com_ocr)

        # Salva o novo PDF pesquisável no disco
        output_pdf.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        
        # Fecha os documentos
        output_pdf.close()
        doc.close()

        success_message = f"SUCESSO: '{output_pdf_path}' foi criado."
        print(success_message)
        return success_message
    except Exception as e:
        error_message = f"ERRO ao processar '{pdf_path.name}': {e}"
        print(error_message)
        return error_message

def processar_pdfs_em_paralelo():
    """
    Lê todos os PDFs no diretório de entrada, aplica OCR em paralelo e salva
    uma versão pesquisável no diretório de saída.
    """
    # 1. Cria o diretório de saída se ele não existir
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Pasta de saída '{OUTPUT_DIR}' pronta.")

    # 2. Encontra todos os arquivos PDF no diretório de entrada
    pdf_files = list(INPUT_DIR.glob('*.pdf'))

    if not pdf_files:
        print(f"Nenhum arquivo PDF encontrado em '{INPUT_DIR.resolve()}'.")
        return

    print(f"Encontrados {len(pdf_files)} PDFs para processar.")

    # 3. Processa os arquivos PDF em paralelo
    # O número de workers pode ser ajustado. O padrão é o número de processadores * 5.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        resultados = list(executor.map(processar_um_pdf, pdf_files))

    print("\n--- Resumo do Processamento ---")
    for resultado in resultados:
        print(resultado)


if __name__ == '__main__':
    processar_pdfs_em_paralelo()
    print("\nProcessamento concluído!")