import csv

from pathlib import Path
from typing import Any

from docx import Document
from pypdf import PdfReader

from app.core.config import get_settings


settings = get_settings()

SUPPORTED_TEXT_EXTENSIONS = {".txt"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_DOCX_EXTENSIONS = {".docx"}
SUPPORTED_CSV_EXTENSIONS = {".csv"}


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


def _extract_docx_text(file_path: Path) -> dict[str, Any]:
    document = Document(str(file_path))

    paragraph_texts = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text and paragraph.text.strip()
    ]

    table_texts: list[str] = []

    for table in document.tables:
        for row in table.rows:
            row_values = [
                cell.text.strip()
                for cell in row.cells
                if cell.text and cell.text.strip()
            ]

            if row_values:
                table_texts.append(" | ".join(row_values))

    extracted_text = "\n".join(paragraph_texts + table_texts).strip()

    if not extracted_text:
        raise ValueError("No extractable text found in DOCX document.")

    return {
        "extraction_method": "python_docx_text",
        "text": extracted_text,
        "metadata": {
            "char_count": len(extracted_text),
            "file_size_bytes": file_path.stat().st_size,
            "paragraph_count": len(paragraph_texts),
            "table_count": len(document.tables),
        },
        "warnings": [],
    }

def _extract_csv_text(file_path: Path) -> dict[str, Any]:
    rows: list[list[str]] = []

    try:
       with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file)

            for row in reader:
                cleaned_row = [
                    cell.strip()
                    for cell in row
                ]
                rows.append(cleaned_row)

    except UnicodeDecodeError as exc:
        raise ValueError("Only UTF-8 or UTF-8-BOM CSV files are currently supported.") from exc

    if not rows:
        raise ValueError("No rows found in CSV file.")

    header = rows[0]
    data_rows = rows[1:]

    text_lines = [
        "ADGS CSV Extracted Document",
        f"Columns: {', '.join(header)}",
        "",
        "Rows:",
    ]

    for row_index, row in enumerate(data_rows, start=1):
        row_pairs = []

        for column_index, cell in enumerate(row):
            column_name = (
                header[column_index]
                if column_index < len(header)
                else f"column_{column_index + 1}"
            )
            row_pairs.append(f"{column_name}: {cell}")

        text_lines.append(f"Row {row_index}: " + " | ".join(row_pairs))

    extracted_text = "\n".join(text_lines).strip()

    return {
        "extraction_method": "csv_text",
        "text": extracted_text,
        "metadata": {
            "char_count": len(extracted_text),
            "file_size_bytes": file_path.stat().st_size,
            "row_count": len(data_rows),
            "column_count": len(header),
            "columns": header,
        },
        "warnings": [],
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
    elif file_extension in SUPPORTED_DOCX_EXTENSIONS:
        extraction_result = _extract_docx_text(file_path)
    elif file_extension in SUPPORTED_CSV_EXTENSIONS:
        extraction_result = _extract_csv_text(file_path)
    else:
        raise ValueError(
            f"Unsupported file type '{file_extension}'. Currently supported: .txt, .pdf, .docx, .csv"
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