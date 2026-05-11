from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


settings = get_settings()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def create_text_embedding(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty when creating an embedding.")

    model = get_embedding_model()
    embedding = model.encode(text.strip())

    return embedding.tolist()


def validate_embedding_size(embedding: list[float]) -> None:
    if len(embedding) != settings.EMBEDDING_VECTOR_SIZE:
        raise ValueError(
            f"Invalid embedding size. Expected {settings.EMBEDDING_VECTOR_SIZE}, "
            f"got {len(embedding)}."
        )