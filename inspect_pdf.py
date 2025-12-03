
from pypdf import PdfReader
from pathlib import Path

def inspect_pdf(pdf_path):
    print(f"Inspecting: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            print(f"--- Page {i+1} ---")
            print(page_text)
            text += page_text
        return text
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Using one of the existing PDFs
    pdf_path = Path(r"c:\Users\bruno\OneDrive - ufpr.br\Documentos\GitHub\CIAI\Relatório Secretariado.pdf")
    inspect_pdf(pdf_path)
