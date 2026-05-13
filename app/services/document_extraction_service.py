from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.core.config import get_settings


settings = get_settings()

SUPPORTED_TEXT_EXTENSIONS = {".txt"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}


def _extract_txt_text(file_path: Path) -> dict[str, Any]:
    try:
        extracted_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Only UTF-8 text files are currently supported.") from exc

    return {
        "extraction_method": "utf8_text",
        "text": extracted_text,
        "metadata": {
            "char_count": len(extracted_text),
            "file_size_bytes": file_path.stat().st_size,
        },
        "warnings": [],
    }


def _extract_pdf_text(file_path: Path) -> dict[str, Any]:
    reader = PdfReader(str(file_path))

    page_texts: list[str] = []
    warnings: list[str] = []

    for page_index, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""

        if not page_text.strip():
            warnings.append(f"No extractable text found on page {page_index + 1}.")

        page_texts.append(page_text)

    extracted_text = "\n\n".join(page_texts).strip()

    if not extracted_text:
        raise ValueError(
            "No extractable text found in PDF. Scanned PDFs will require OCR support later."
        )

    return {
        "extraction_method": "pypdf_text",
        "text": extracted_text,
        "metadata": {
            "char_count": len(extracted_text),
            "file_size_bytes": file_path.stat().st_size,
            "page_count": len(reader.pages),
        },
        "warnings": warnings,
    }


def extract_document_text(stored_filename: str) -> dict[str, Any]:
    if not stored_filename:
        raise ValueError("stored_filename is missing.")

    file_path = Path(settings.UPLOAD_DIR) / stored_filename

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_extension = file_path.suffix.lower()

    if file_extension in SUPPORTED_TEXT_EXTENSIONS:
        extraction_result = _extract_txt_text(file_path)
    elif file_extension in SUPPORTED_PDF_EXTENSIONS:
        extraction_result = _extract_pdf_text(file_path)
    else:
        raise ValueError(
            f"Unsupported file type '{file_extension}'. Currently supported: .txt, .pdf"
        )

    return {
        "stored_filename": stored_filename,
        "file_path": str(file_path),
        "file_extension": file_extension,
        "extraction_method": extraction_result["extraction_method"],
        "text": extraction_result["text"],
        "metadata": extraction_result["metadata"],
        "warnings": extraction_result["warnings"],
    }