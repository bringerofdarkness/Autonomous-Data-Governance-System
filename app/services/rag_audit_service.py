from typing import Any

from app.models import RagSearchAuditLog, User


def create_rag_search_audit_log(
    current_user: User,
    query: str,
    result_limit: int,
    min_score: float,
    search_result: dict[str, Any],
) -> RagSearchAuditLog:
    matches = search_result.get("matches", [])

    matched_document_ids = [
        match.get("document_id")
        for match in matches
        if match.get("document_id")
    ]

    matched_point_ids = [
        match.get("point_id")
        for match in matches
        if match.get("point_id")
    ]

    # Use synchronous Django ORM creation
    audit_log = RagSearchAuditLog.objects.create(
        actor_user=current_user,
        query=query,
        result_limit=result_limit,
        min_score=min_score,
        matches_count=search_result.get("matches_count", 0),
        matched_document_ids=matched_document_ids,
        matched_point_ids=matched_point_ids,
        extra_data={
            "matched_documents": [
                {
                    "point_id": match.get("point_id"),
                    "document_id": match.get("document_id"),
                    "original_filename": match.get("original_filename"),
                    "document_category": match.get("document_category"),
                    "risk_score": match.get("risk_score"),
                    "chunk_index": match.get("chunk_index"),
                    "score": match.get("score"),
                    "source": match.get("source"),
                }
                for match in matches
            ]
        },
    )

    return audit_log
