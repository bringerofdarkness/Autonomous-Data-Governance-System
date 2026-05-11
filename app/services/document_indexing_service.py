import uuid
from typing import Any

from qdrant_client.models import PointStruct

from app.core.config import get_settings
from app.services.cleaned_text_service import read_cleaned_text
from app.services.embedding_service import create_text_embedding, validate_embedding_size
from app.services.qdrant_service import ensure_gold_collection, get_qdrant_client
from app.services.text_chunking_service import split_text_into_chunks


settings = get_settings()


def build_chunk_point_id(document_id: uuid.UUID, chunk_index: int) -> str:
    chunk_uuid = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"adgs:{document_id}:chunk:{chunk_index}",
    )
    return str(chunk_uuid)


def index_cleaned_document_in_qdrant(
    document_id: uuid.UUID,
    original_filename: str,
    cleaned_text_filename: str,
    document_category: str | None,
    risk_score: int | None,
) -> dict[str, Any]:
    ensure_gold_collection()

    cleaned_text = read_cleaned_text(cleaned_text_filename)

    document_embedding = create_text_embedding(cleaned_text)
    validate_embedding_size(document_embedding)

    chunks = split_text_into_chunks(cleaned_text)
    client = get_qdrant_client()

    document_payload = {
        "point_type": "DOCUMENT",
        "document_id": str(document_id),
        "original_filename": original_filename,
        "cleaned_text_filename": cleaned_text_filename,
        "document_category": document_category,
        "risk_score": risk_score,
        "source": "ADGS_GOLD_COLLECTION",
    }

    points: list[PointStruct] = [
        PointStruct(
            id=str(document_id),
            vector=document_embedding,
            payload=document_payload,
        )
    ]

    for chunk in chunks:
        chunk_embedding = create_text_embedding(chunk["chunk_text"])
        validate_embedding_size(chunk_embedding)

        chunk_payload = {
            "point_type": "CHUNK",
            "document_id": str(document_id),
            "chunk_id": build_chunk_point_id(
                document_id=document_id,
                chunk_index=chunk["chunk_index"],
            ),
            "chunk_index": chunk["chunk_index"],
            "chunk_text": chunk["chunk_text"],
            "start_char": chunk["start_char"],
            "end_char": chunk["end_char"],
            "char_count": chunk["char_count"],
            "original_filename": original_filename,
            "cleaned_text_filename": cleaned_text_filename,
            "document_category": document_category,
            "risk_score": risk_score,
            "source": "ADGS_GOLD_COLLECTION",
        }

        points.append(
            PointStruct(
                id=build_chunk_point_id(
                    document_id=document_id,
                    chunk_index=chunk["chunk_index"],
                ),
                vector=chunk_embedding,
                payload=chunk_payload,
            )
        )

    client.upsert(
        collection_name=settings.QDRANT_GOLD_COLLECTION,
        points=points,
    )

    return {
        "qdrant_point_id": document_id,
        "collection_name": settings.QDRANT_GOLD_COLLECTION,
        "vector_size": len(document_embedding),
        "chunks_indexed": len(chunks),
        "points_indexed": len(points),
        "payload": document_payload,
    }