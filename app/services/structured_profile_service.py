import re
from typing import Any


SENSITIVE_FIELD_RULES: list[tuple[str, str]] = [
    ("EMAIL", r"\b(email|e-mail|mail_address)\b"),
    ("PHONE", r"\b(phone|mobile|telephone|contact_number|contact_no)\b"),
    ("EMPLOYEE_ID", r"\b(employee[\s_.-]*id|emp[\s_.-]*id|staff[\s_.-]*id)\b"),
    ("PERSON_NAME", r"\b(name|full[\s_.-]*name|person[\s_.-]*name|employee[\s_.-]*name|customer[\s_.-]*name|client[\s_.-]*name)\b"),
    ("ADDRESS", r"\b(address|home[\s_.-]*address|office[\s_.-]*address|location)\b"),
    ("DATE_OF_BIRTH", r"\b(date[\s_.-]*of[\s_.-]*birth|dob|birth[\s_.-]*date)\b"),
    ("NATIONAL_ID", r"\b(national[\s_.-]*id|nid|ssn|social[\s_.-]*security)\b"),
    ("PASSPORT", r"\b(passport|passport[\s_.-]*number)\b"),
    ("BANK_ACCOUNT", r"\b(bank[\s_.-]*account|account[\s_.-]*number|iban|routing[\s_.-]*number)\b"),
    ("SALARY", r"\b(salary|wage|payroll|compensation)\b"),
]


def _normalize_field_name(field_name: str) -> str:
    return field_name.strip().lower()


def _detect_field_sensitivity(field_name: str) -> str | None:
    normalized_name = _normalize_field_name(field_name)

    for sensitivity_type, pattern in SENSITIVE_FIELD_RULES:
        if re.search(pattern, normalized_name, re.IGNORECASE):
            return sensitivity_type

    return None


def _extract_json_field_names(extracted_text: str) -> list[str]:
    field_names: list[str] = []

    for line in extracted_text.splitlines():
        line = line.strip()

        if not line or line in {"ADGS JSON Extracted Document", "Fields:"}:
            continue

        if ":" not in line:
            continue

        field_name = line.split(":", 1)[0].strip()

        if field_name:
            field_names.append(field_name)

    return field_names


def _extract_csv_columns(extraction_metadata: dict[str, Any]) -> list[str]:
    columns = extraction_metadata.get("columns", [])

    if not isinstance(columns, list):
        return []

    return [
        str(column).strip()
        for column in columns
        if str(column).strip()
    ]


def _extract_xlsx_columns(extraction_metadata: dict[str, Any]) -> list[dict[str, str]]:
    sensitive_candidates: list[dict[str, str]] = []

    sheets = extraction_metadata.get("sheets", [])

    if not isinstance(sheets, list):
        return []

    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue

        sheet_name = str(sheet.get("sheet_name", "Unknown Sheet"))
        columns = sheet.get("columns", [])

        if not isinstance(columns, list):
            continue

        for column in columns:
            column_name = str(column).strip()

            if column_name:
                sensitive_candidates.append(
                    {
                        "sheet_name": sheet_name,
                        "field_name": column_name,
                    }
                )

    return sensitive_candidates


def build_structured_profile(
    extraction_method: str | None,
    extraction_metadata: dict[str, Any] | None,
    extracted_text: str | None,
) -> dict[str, Any]:
    extraction_metadata = extraction_metadata or {}
    extracted_text = extracted_text or ""

    if extraction_method not in {"csv_text", "openpyxl_xlsx_text", "json_text"}:
        return {
            "profile_type": "unstructured_or_unknown",
            "is_structured": False,
            "sensitive_field_count": 0,
            "sensitive_fields": [],
            "governance_notes": [],
        }

    sensitive_fields: list[dict[str, Any]] = []

    if extraction_method == "csv_text":
        for column_name in _extract_csv_columns(extraction_metadata):
            sensitivity_type = _detect_field_sensitivity(column_name)

            if sensitivity_type:
                sensitive_fields.append(
                    {
                        "field_name": column_name,
                        "sensitivity_type": sensitivity_type,
                    }
                )

    elif extraction_method == "openpyxl_xlsx_text":
        for item in _extract_xlsx_columns(extraction_metadata):
            field_name = item["field_name"]
            sensitivity_type = _detect_field_sensitivity(field_name)

            if sensitivity_type:
                sensitive_fields.append(
                    {
                        "sheet_name": item["sheet_name"],
                        "field_name": field_name,
                        "sensitivity_type": sensitivity_type,
                    }
                )

    elif extraction_method == "json_text":
        for field_name in _extract_json_field_names(extracted_text):
            sensitivity_type = _detect_field_sensitivity(field_name)

            if sensitivity_type:
                sensitive_fields.append(
                    {
                        "field_name": field_name,
                        "sensitivity_type": sensitivity_type,
                    }
                )

    governance_notes: list[str] = []

    if sensitive_fields:
        governance_notes.append(
            "Structured document contains sensitive fields that require governance review."
        )

    return {
        "profile_type": "structured_data",
        "is_structured": True,
        "extraction_method": extraction_method,
        "sensitive_field_count": len(sensitive_fields),
        "sensitive_fields": sensitive_fields,
        "governance_notes": governance_notes,
    }
