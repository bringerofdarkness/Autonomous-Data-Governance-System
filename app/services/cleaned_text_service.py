from pathlib import Path

from app.core.config import get_settings


settings = get_settings()


def save_cleaned_text(document_id: str, cleaned_text: str) -> str:
    if not cleaned_text or not cleaned_text.strip():
        raise ValueError("Cleaned text cannot be empty.")

    cleaned_dir = Path(settings.CLEANED_TEXT_DIR)
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    cleaned_filename = f"{document_id}.txt"
    cleaned_file_path = cleaned_dir / cleaned_filename

    cleaned_file_path.write_text(cleaned_text, encoding="utf-8")

    return cleaned_filename


def read_cleaned_text(cleaned_filename: str) -> str:
    cleaned_file_path = Path(settings.CLEANED_TEXT_DIR) / cleaned_filename

    if not cleaned_file_path.exists():
        raise FileNotFoundError(f"Cleaned text file not found: {cleaned_file_path}")

    return cleaned_file_path.read_text(encoding="utf-8")