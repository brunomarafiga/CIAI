
import pytesseract
from PIL import Image
import sys

# Configure Tesseract path (copied from ocr.py)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='por')
        print("--- Extracted Text ---")
        print(text)
        print("----------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    image_path = r"C:/Users/bruno/.gemini/antigravity/brain/19c87e6d-0a01-4873-bc68-97a114e2b74b/uploaded_image_1764784688563.png"
    extract_text_from_image(image_path)
