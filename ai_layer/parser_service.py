from pathlib import Path

import docx
import fitz
from PIL import Image
import pytesseract


class ParserService:
    @staticmethod
    def parse(file_path: Path, content_type: str) -> tuple[str, str]:
        extension = file_path.suffix.lower()
        if content_type == "application/pdf" or extension == ".pdf":
            return ParserService._parse_pdf(file_path), "pdf"
        if content_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ) or extension in (".docx", ".doc"):
            return ParserService._parse_docx(file_path), "docx"
        if content_type.startswith("image/") or extension in (".png", ".jpg", ".jpeg", ".webp"):
            return ParserService._parse_image(file_path), "image"
        return file_path.read_text(encoding="utf-8", errors="ignore"), "text"

    @staticmethod
    def _parse_pdf(file_path: Path) -> str:
        text_parts: list[str] = []
        with fitz.open(file_path) as pdf_document:
            for page in pdf_document:
                text_parts.append(page.get_text("text"))
        return "\n".join(text_parts).strip()

    @staticmethod
    def _parse_docx(file_path: Path) -> str:
        document = docx.Document(file_path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text).strip()

    @staticmethod
    def _parse_image(file_path: Path) -> str:
        image = Image.open(file_path)
        return pytesseract.image_to_string(image).strip()
