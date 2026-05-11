from typing import Any


DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100


def normalize_text_for_chunking(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for chunking.")

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return "\n".join(lines)


def split_text_into_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    normalized_text = normalize_text_for_chunking(text)

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    chunks: list[dict[str, Any]] = []

    text_length = len(normalized_text)
    start = 0
    chunk_index = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text = normalized_text[start:end].strip()

        if chunk_text:
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "start_char": start,
                    "end_char": end,
                    "char_count": len(chunk_text),
                }
            )
            chunk_index += 1

        if end >= text_length:
            break

        start = end - chunk_overlap

    return chunks