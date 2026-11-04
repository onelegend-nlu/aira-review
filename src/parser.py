"""
Đọc PDF bằng PyMuPDF.

- Trang có text layer: lấy text như trước.
- Trang KHÔNG có text (PDF scan): nếu AIRA_OCR=1 và máy đã cài
  pytesseract + Pillow + tesseract, thử OCR trang đó.
  Chưa cài / OCR lỗi -> bỏ qua trang như hành vi cũ, không crash.
"""

import pymupdf

from src.config import OCR_ENABLED


def _ocr_page(page):
    try:
        import io

        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    try:
        pixmap = page.get_pixmap(dpi=200)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))

        try:
            return pytesseract.image_to_string(
                image, lang="vie+eng"
            )
        except Exception:
            return pytesseract.image_to_string(image, lang="eng")

    except Exception as error:
        print(f"OCR failed for a page: {error}")
        return ""


def read_pdf(path):
    doc = pymupdf.open(path)

    pages = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")

        if not text.strip() and OCR_ENABLED:
            text = _ocr_page(page)

        if text.strip():
            pages.append({
                "page": page_number,
                "text": text
            })

    return pages
