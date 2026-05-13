from collections import Counter
from typing import Any


PII_TYPE_WEIGHTS = {
    "PERSON_NAME": 15,
    "EMAIL": 15,
    "PHONE": 15,
    "EMPLOYEE_ID": 20,
    "ADDRESS": 20,
    "DATE_OF_BIRTH": 30,
    "NATIONAL_ID": 30,
    "PASSPORT": 30,
    "BANK_ACCOUNT": 30,
    "SALARY": 20,
}


STRUCTURED_EXTRACTION_METHODS = {
    "csv_text",
    "openpyxl_xlsx_text",
    "json_text",
}


def calculate_governance_risk(
    detected_pii: list[dict[str, str]] | None,
    conflict_found: bool = False,
    structured_profile: dict[str, Any] | None = None,
    extraction_method: str | None = None,
) -> dict[str, Any]:
    detected_pii = detected_pii or []
    structured_profile = structured_profile or {}

    pii_type_counts = Counter(
        item.get("type", "UNKNOWN")
        for item in detected_pii
    )

    pii_score = 0

    for pii_type, count in pii_type_counts.items():
        pii_score += PII_TYPE_WEIGHTS.get(pii_type, 10) * count

    pii_score = min(pii_score, 70)

    sensitive_field_count = int(
        structured_profile.get("sensitive_field_count", 0) or 0
    )

    structured_field_score = min(sensitive_field_count * 5, 20)

    structured_file_bonus = 0

    if (
        extraction_method in STRUCTURED_EXTRACTION_METHODS
        and sensitive_field_count > 0
    ):
        structured_file_bonus = 5

    conflict_score = 30 if conflict_found else 0

    total_score = min(
        pii_score
        + structured_field_score
        + structured_file_bonus
        + conflict_score,
        100,
    )

    if conflict_found or total_score >= 75:
        risk_level = "HIGH"
    elif total_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    risk_factors: list[str] = []

    if detected_pii:
        risk_factors.append(
            f"Detected {len(detected_pii)} PII item(s)."
        )

    if sensitive_field_count > 0:
        risk_factors.append(
            f"Detected {sensitive_field_count} sensitive structured field(s)."
        )

    if conflict_found:
        risk_factors.append(
            "Potential conflict found against approved Gold Collection."
        )

    if extraction_method in STRUCTURED_EXTRACTION_METHODS:
        risk_factors.append(
            f"Structured extraction method used: {extraction_method}."
        )

    return {
        "risk_score": total_score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "score_breakdown": {
            "pii_score": pii_score,
            "structured_field_score": structured_field_score,
            "structured_file_bonus": structured_file_bonus,
            "conflict_score": conflict_score,
        },
        "pii_type_counts": dict(pii_type_counts),
        "sensitive_field_count": sensitive_field_count,
    }
