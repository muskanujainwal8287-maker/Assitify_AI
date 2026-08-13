import io
import os
import shutil
import sys
from pathlib import Path

import docx
import fitz
from PIL import Image
import pytesseract


def _resolve_tesseract_cmd() -> str | None:
    env = (os.environ.get("TESSERACT_CMD") or "").strip()
    if env and Path(env).is_file():
        return env
    found = shutil.which("tesseract")
    if found:
        return found
    if sys.platform == "win32":
        for candidate in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ):
            if Path(candidate).is_file():
                return candidate
    return None


_tess = _resolve_tesseract_cmd()
if _tess:
    pytesseract.pytesseract.tesseract_cmd = _tess


class ParserService:
    @staticmethod
    def parse_bytes(content: bytes, filename: str, content_type: str) -> tuple[str, str]:
        extension = Path(filename).suffix.lower()
        content_type = content_type or ""
        if content_type == "application/pdf" or extension == ".pdf":
            return ParserService._parse_pdf(content), "pdf"
        if content_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ) or extension in (".docx", ".doc"):
            return ParserService._parse_docx(content), "docx"
        if content_type.startswith("image/") or extension in (".png", ".jpg", ".jpeg", ".webp"):
            return ParserService._parse_image(content), "image"
        return content.decode("utf-8", errors="ignore"), "text"

    @staticmethod
    def _parse_pdf(content: bytes) -> str:
        text_parts: list[str] = []
        with fitz.open(stream=content, filetype="pdf") as pdf_document:
            for page in pdf_document:
                text_parts.append(page.get_text("text"))
        return "\n".join(text_parts).strip()

    @staticmethod
    def _parse_docx(content: bytes) -> str:
        document = docx.Document(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text).strip()

    @staticmethod
    def _parse_image(content: bytes) -> str:
        image = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(image).strip()
