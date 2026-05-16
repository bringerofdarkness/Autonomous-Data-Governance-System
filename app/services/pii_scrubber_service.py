import re
from typing import Any


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4})"
)

EMPLOYEE_ID_PATTERN = re.compile(
    r"\bEMP[-_\s]?\d{3,10}\b",
    re.IGNORECASE,
)


LABELLED_EMPLOYEE_ID_PATTERN = re.compile(
    r"\b(?P<label>"
    r"Employee ID|Employee Id|Employee No|Employee Number|Staff ID|Staff No|"
    r"User ID|User Id|Personnel ID|Personnel No|"
    r"(?:[A-Za-z0-9_]+\.)*(?:employee_id|staff_id|user_id|personnel_id)"
    r")\s*:\s*"
    r"(?P<employee_id>[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+){1,5})\b",
    re.IGNORECASE,
)

LABELLED_PERSON_NAME_PATTERN = re.compile(
    r"\b(?P<label>"
    r"Employee Name|Customer Name|Client Name|User Name|Full Name|"
    r"Contact Person|Contact person|Person Name|"
    r"(?:[A-Za-z0-9_]+\.)*(?:name|full_name|person_name|employee_name|customer_name|client_name)"
    r")\s*:\s*"
    r"(?P<name>[A-Z][A-Za-z'.-]+(?:[ \t]+[A-Z][A-Za-z'.-]+){0,3})",
    re.IGNORECASE,
)


def detect_and_redact_pii(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        return {
            "cleaned_text": text,
            "detected_pii": [],
        }

    cleaned_text = text
    detected_pii: list[dict[str, str]] = []

    def replace_labelled_name(match: re.Match[str]) -> str:
        label = match.group("label")
        person_name = match.group("name")

        detected_pii.append(
            {
                "type": "PERSON_NAME",
                "value": person_name,
            }
        )

        return f"{label}: [REDACTED_PERSON_NAME]"

    cleaned_text = LABELLED_PERSON_NAME_PATTERN.sub(
        replace_labelled_name,
        cleaned_text,
    )

    for match in EMAIL_PATTERN.finditer(cleaned_text):
        detected_pii.append(
            {
                "type": "EMAIL",
                "value": match.group(0),
            }
        )

    cleaned_text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", cleaned_text)

    for match in PHONE_PATTERN.finditer(cleaned_text):
        detected_pii.append(
            {
                "type": "PHONE",
                "value": match.group(0),
            }
        )

    cleaned_text = PHONE_PATTERN.sub("[REDACTED_PHONE]", cleaned_text)

    def replace_labelled_employee_id(match: re.Match[str]) -> str:
        label = match.group("label")
        employee_id = match.group("employee_id")

        detected_pii.append(
            {
                "type": "EMPLOYEE_ID",
                "value": employee_id,
            }
        )

        return f"{label}: [REDACTED_EMPLOYEE_ID]"

    cleaned_text = LABELLED_EMPLOYEE_ID_PATTERN.sub(
        replace_labelled_employee_id,
        cleaned_text,
    )

    for match in EMPLOYEE_ID_PATTERN.finditer(cleaned_text):
        detected_pii.append(
            {
                "type": "EMPLOYEE_ID",
                "value": match.group(0),
            }
        )

    cleaned_text = EMPLOYEE_ID_PATTERN.sub(
        "[REDACTED_EMPLOYEE_ID]",
        cleaned_text,
    )

    return {
        "cleaned_text": cleaned_text,
        "detected_pii": detected_pii,
    }