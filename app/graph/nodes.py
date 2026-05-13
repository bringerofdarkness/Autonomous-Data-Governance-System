import re, uuid

from pathlib import Path

from langgraph.types import interrupt

from app.services.governance_risk_service import calculate_governance_risk
from app.services.structured_profile_service import build_structured_profile
from app.services.document_extraction_service import extract_document_text
from app.services.pii_scrubber_service import detect_and_redact_pii
from app.services.conflict_service import check_text_conflicts
from app.core.config import get_settings
from app.graph.state import ADGSGraphState


settings = get_settings()


EMAIL_PATTERN = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
PHONE_PATTERN = re.compile(r"(\+?\d[\d\s\-\(\)]{7,}\d)")
EMPLOYEE_ID_PATTERN = re.compile(r"\bEMP-\d{3,10}\b", re.IGNORECASE)


def text_loader_node(state: ADGSGraphState) -> ADGSGraphState:
    stored_filename = state.get("stored_filename")

    if not stored_filename:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": "stored_filename is missing from graph state.",
        }

    try:
        extraction_result = extract_document_text(stored_filename)
        raw_text = extraction_result["text"]

        return {
            **state,
            "raw_text": raw_text,
            "extraction_metadata": extraction_result["metadata"],
            "extraction_method": extraction_result["extraction_method"],
            "current_step": "TEXT_EXTRACTED",
            "error_message": None,
        }

    except Exception as exc:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": f"Document extraction failed: {exc}",
        }


def categorizer_node(state: ADGSGraphState) -> ADGSGraphState:
    raw_text = state.get("raw_text", "").lower()

    if not raw_text:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": "raw_text is missing. Cannot categorize document.",
        }

    if "policy" in raw_text:
        category = "Policy"
    elif "employee" in raw_text or "hr" in raw_text:
        category = "HR"
    elif "invoice" in raw_text or "payment" in raw_text:
        category = "Finance"
    elif "contract" in raw_text or "agreement" in raw_text:
        category = "Legal"
    else:
        category = "General"

    return {
        **state,
        "document_category": category,
        "current_step": "CATEGORIZED",
        "error_message": None,
    }


def pii_scrubber_node(state: ADGSGraphState) -> ADGSGraphState:
    raw_text = state.get("raw_text", "")

    if not raw_text:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": "raw_text is missing. Cannot scrub PII.",
        }

    try:
        pii_result = detect_and_redact_pii(raw_text)

        return {
            **state,
            "cleaned_text": pii_result["cleaned_text"],
            "detected_pii": pii_result["detected_pii"],
            "current_step": "PII_SCRUBBED",
            "error_message": None,
        }

    except Exception as exc:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": f"PII scrubber failed: {exc}",
        }

def conflict_agent_node(state: ADGSGraphState) -> ADGSGraphState:
    document_id = state.get("document_id")
    cleaned_text = state.get("cleaned_text", "")

    if not document_id:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": "document_id is missing. Cannot run conflict check.",
        }

    if not cleaned_text:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": "cleaned_text is missing. Cannot run conflict check.",
        }

    try:
        conflict_result = check_text_conflicts(
            document_id=uuid.UUID(document_id),
            cleaned_text=cleaned_text,
            similarity_threshold=0.75,
            limit=5,
        )

        potential_conflicts = conflict_result["potential_conflicts"]

        if conflict_result["conflict_found"]:
            top_match = potential_conflicts[0]
            conflict_summary = (
                f"Potential conflict found with Qdrant point "
                f"{top_match['point_id']} at similarity score {top_match['score']:.4f}."
            )
        else:
            conflict_summary = "No potential conflict found in Qdrant Gold collection."

        return {
            **state,
            "conflict_found": conflict_result["conflict_found"],
            "conflict_summary": conflict_summary,
            "current_step": "CONFLICT_CHECKED",
            "error_message": None,
        }

    except Exception as exc:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": f"Conflict Agent failed: {exc}",
        }

def critic_node(state: ADGSGraphState) -> ADGSGraphState:
    detected_pii = state.get("detected_pii", [])
    conflict_found = state.get("conflict_found", False)

    pii_count = len(detected_pii)

    if conflict_found:
        return {
            **state,
            "risk_level": "HIGH",
            "requires_admin_approval": True,
            "critic_feedback": "Conflict detected. Admin approval is required before indexing.",
            "current_step": "WAITING_FOR_ADMIN",
            "error_message": None,
        }

    if pii_count >= 3:
        return {
            **state,
            "risk_level": "HIGH",
            "requires_admin_approval": True,
            "critic_feedback": "High PII exposure detected. Admin approval is required.",
            "current_step": "WAITING_FOR_ADMIN",
            "error_message": None,
        }

    if pii_count > 0:
        return {
            **state,
            "risk_level": "MEDIUM",
            "requires_admin_approval": False,
            "critic_feedback": "PII was detected and redacted. Document can proceed.",
            "current_step": "CRITIC_REVIEWED",
            "error_message": None,
        }

    return {
        **state,
        "risk_level": "LOW",
        "requires_admin_approval": False,
        "critic_feedback": "No PII or conflict detected. Document can proceed.",
        "current_step": "CRITIC_REVIEWED",
        "error_message": None,
    }


def hitl_review_node(state: ADGSGraphState) -> ADGSGraphState:
    detected_pii = state.get("detected_pii", [])
    extraction_method = state.get("extraction_method")
    extraction_metadata = state.get("extraction_metadata", {})

    structured_profile = build_structured_profile(
        extraction_method=extraction_method,
        extraction_metadata=extraction_metadata,
        extracted_text=state.get("raw_text"),
    )

    risk_result = calculate_governance_risk(
        detected_pii=detected_pii,
        conflict_found=state.get("conflict_found", False),
        structured_profile=structured_profile,
        extraction_method=extraction_method,
    )

    human_decision = interrupt(
        {
            "type": "ADMIN_REVIEW_REQUIRED",
            "document_id": state.get("document_id"),
            "original_filename": state.get("original_filename"),
            "document_category": state.get("document_category"),
            "risk_score": risk_result["risk_score"],
            "risk_level": risk_result["risk_level"],
            "risk_result": risk_result,
            "structured_profile": structured_profile,
            "extraction_method": extraction_method,
            "extraction_metadata": extraction_metadata,
            "detected_pii_count": len(detected_pii),
            "conflict_found": state.get("conflict_found", False),
            "conflict_summary": state.get("conflict_summary"),
            "critic_feedback": state.get("critic_feedback"),
            "question": "Admin approval is required. Approve or reject this document?",
        }
    )

    decision = human_decision.get("decision")
    reason = human_decision.get("reason")

    if decision not in {"approve", "reject"}:
        return {
            **state,
            "current_step": "FAILED",
            "error_message": "Invalid HITL decision. Expected 'approve' or 'reject'.",
        }

    return {
        **state,
        "hitl_decision": decision,
        "hitl_reason": reason,
        "current_step": "HITL_REVIEW_COMPLETED",
        "error_message": None,
    }

