import uuid
from typing import Any

from app.services.cleaned_text_service import read_cleaned_text
from app.services.embedding_service import create_text_embedding, validate_embedding_size
from app.services.qdrant_service import search_gold_collection


def check_document_conflicts(
    document_id: uuid.UUID,
    cleaned_text_filename: str,
    similarity_threshold: float = 0.75,
    limit: int = 5,
) -> dict[str, Any]:
    cleaned_text = read_cleaned_text(cleaned_text_filename)

    query_vector = create_text_embedding(cleaned_text)
    validate_embedding_size(query_vector)

    results = search_gold_collection(
        query_vector=query_vector,
        limit=limit,
    )

    # Do not count the same document as its own conflict.
    filtered_results = [
        result
        for result in results
        if result["point_id"] != str(document_id)
    ]

    potential_conflicts = [
        result
        for result in filtered_results
        if result["score"] >= similarity_threshold
    ]

    return {
        "conflict_found": len(potential_conflicts) > 0,
        "similarity_threshold": similarity_threshold,
        "matches_checked": len(filtered_results),
        "potential_conflicts": potential_conflicts,
    }

def check_text_conflicts(
    document_id: uuid.UUID,
    cleaned_text: str,
    similarity_threshold: float = 0.75,
    limit: int = 5,
) -> dict[str, Any]:
    if not cleaned_text or not cleaned_text.strip():
        return {
            "conflict_found": False,
            "similarity_threshold": similarity_threshold,
            "matches_checked": 0,
            "potential_conflicts": [],
        }

    query_vector = create_text_embedding(cleaned_text)
    validate_embedding_size(query_vector)

    results = search_gold_collection(
        query_vector=query_vector,
        limit=limit,
    )

    filtered_results = [
        result
        for result in results
        if result["point_id"] != str(document_id)
    ]

    potential_conflicts = [
        result
        for result in filtered_results
        if result["score"] >= similarity_threshold
    ]

    return {
        "conflict_found": len(potential_conflicts) > 0,
        "similarity_threshold": similarity_threshold,
        "matches_checked": len(filtered_results),
        "potential_conflicts": potential_conflicts,
    }