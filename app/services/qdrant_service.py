from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, VectorParams

from app.core.config import get_settings


settings = get_settings()


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


def check_qdrant_health() -> dict[str, str]:
    client = get_qdrant_client()

    collections = client.get_collections()

    return {
        "status": "healthy",
        "qdrant_url": settings.QDRANT_URL,
        "collections_count": str(len(collections.collections)),
    }


def ensure_gold_collection() -> dict[str, str]:
    client = get_qdrant_client()
    collection_name = settings.QDRANT_GOLD_COLLECTION

    collections = client.get_collections()
    existing_collection_names = {
        collection.name
        for collection in collections.collections
    }

    if collection_name in existing_collection_names:
        return {
            "status": "exists",
            "collection_name": collection_name,
            "vector_size": str(settings.QDRANT_VECTOR_SIZE),
            "distance": "COSINE",
        }

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.QDRANT_VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )

    return {
        "status": "created",
        "collection_name": collection_name,
        "vector_size": str(settings.QDRANT_VECTOR_SIZE),
        "distance": "COSINE",
    }

def get_gold_collection_point(point_id: str) -> dict:
    client = get_qdrant_client()

    points = client.retrieve(
        collection_name=settings.QDRANT_GOLD_COLLECTION,
        ids=[point_id],
        with_payload=True,
        with_vectors=False,
    )

    if not points:
        return {
            "found": False,
            "point_id": point_id,
            "collection_name": settings.QDRANT_GOLD_COLLECTION,
            "payload": None,
        }

    point = points[0]

    return {
        "found": True,
        "point_id": str(point.id),
        "collection_name": settings.QDRANT_GOLD_COLLECTION,
        "payload": point.payload,
    }


def search_gold_collection(
    query_vector: list[float],
    limit: int = 5,
) -> list[dict]:
    client = get_qdrant_client()

    search_results = client.search(
        collection_name=settings.QDRANT_GOLD_COLLECTION,
        query_vector=query_vector,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    return [
        {
            "point_id": str(result.id),
            "score": result.score,
            "payload": result.payload,
        }
        for result in search_results
    ]

def get_gold_collection_chunks_for_document(
    document_id: str,
    limit: int = 50,
) -> list[dict]:
    client = get_qdrant_client()

    points, _ = client.scroll(
        collection_name=settings.QDRANT_GOLD_COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                ),
                FieldCondition(
                    key="point_type",
                    match=MatchValue(value="CHUNK"),
                ),
            ]
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    chunks = [
        {
            "point_id": str(point.id),
            "payload": point.payload,
        }
        for point in points
    ]

    chunks.sort(
        key=lambda item: item["payload"].get("chunk_index", 0)
        if item.get("payload")
        else 0
    )

    return chunks

def search_gold_collection_chunks(
    query_vector: list[float],
    limit: int = 5,
) -> list[dict]:
    client = get_qdrant_client()

    search_results = client.search(
        collection_name=settings.QDRANT_GOLD_COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="point_type",
                    match=MatchValue(value="CHUNK"),
                ),
            ]
        ),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    return [
        {
            "point_id": str(result.id),
            "score": result.score,
            "payload": result.payload,
        }
        for result in search_results
    ]