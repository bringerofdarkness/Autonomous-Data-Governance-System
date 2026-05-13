from typing import Any

from app.services.embedding_service import create_text_embedding, validate_embedding_size
from app.services.qdrant_service import search_gold_collection_chunks


def search_approved_gold_chunks(
    query: str,
    limit: int = 5,
    min_score: float = 0.30,
) -> dict[str, Any]:
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    query_embedding = create_text_embedding(query.strip())
    validate_embedding_size(query_embedding)

    results = search_gold_collection_chunks(
        query_vector=query_embedding,
        limit=limit,
    )

    matches = []

    for result in results:
        payload = result.get("payload") or {}
        if result["score"] < min_score:
            continue

        matches.append(
            {
                "point_id": result["point_id"],
                "score": result["score"],
                "document_id": payload.get("document_id"),
                "original_filename": payload.get("original_filename"),
                "document_category": payload.get("document_category"),
                "risk_score": payload.get("risk_score"),
                "chunk_index": payload.get("chunk_index"),
                "chunk_text": payload.get("chunk_text"),
                "source": payload.get("source"),
            }
        )

    return {
        "query": query,
        "min_score": min_score,
        "matches_count": len(matches),
        "matches": matches,
    }