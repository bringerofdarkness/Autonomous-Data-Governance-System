from pathlib import Path
from typing import Any

from app.core.config import get_settings


settings = get_settings()

SUPPORTED_TEXT_EXTENSIONS = {".txt"}


def extract_document_text(stored_filename: str) -> dict[str, Any]:
    if not stored_filename:
        raise ValueError("stored_filename is missing.")

    file_path = Path(settings.UPLOAD_DIR) / stored_filename

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_extension = file_path.suffix.lower()

    if file_extension not in SUPPORTED_TEXT_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{file_extension}'. Currently supported: .txt"
        )

    try:
        extracted_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Only UTF-8 text files are currently supported.") from exc

    return {
        "stored_filename": stored_filename,
        "file_path": str(file_path),
        "file_extension": file_extension,
        "extraction_method": "utf8_text",
        "text": extracted_text,
        "metadata": {
            "char_count": len(extracted_text),
            "file_size_bytes": file_path.stat().st_size,
        },
        "warnings": [],
    }
