from typing import Any, Literal, TypedDict


DocumentRiskLevel = Literal["LOW", "MEDIUM", "HIGH"]

DocumentProcessingStep = Literal[
    "STARTED",
    "TEXT_EXTRACTED",
    "CATEGORIZED",
    "PII_SCRUBBED",
    "CONFLICT_CHECKED",
    "CRITIC_REVIEWED",
    "WAITING_FOR_ADMIN",
    "APPROVED",
    "REJECTED",
    "FAILED",
]


class ADGSGraphState(TypedDict, total=False):
    document_id: str
    stored_filename: str
    original_filename: str

    raw_text: str
    cleaned_text: str 
    
    extraction_method: str | None
    extraction_metadata: dict[str, Any]
    extraction_warnings: list[str]

    document_category: str | None
    detected_pii: list[dict[str, str]]

    conflict_found: bool
    conflict_summary: str | None

    risk_level: DocumentRiskLevel
    critic_feedback: str | None

    requires_admin_approval: bool
    admin_decision: str | None

    current_step: DocumentProcessingStep
    error_message: str | None

    hitl_decision: str | None
    hitl_reason: str | None