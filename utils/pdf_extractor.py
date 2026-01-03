import pdfplumber
import pytesseract
from PIL import Image
import io

def extract_text_and_images(pdf_bytes: bytes):
    text = ""
    images = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

            try:
                img = page.to_image(resolution=200).original
                images.append(img)
            except:
                pass

    return text.strip(), images


def ocr_images(images):
    ocr_text = ""
    for img in images:
        ocr_text += pytesseract.image_to_string(img) + "\n"
    return ocr_text.strip()
