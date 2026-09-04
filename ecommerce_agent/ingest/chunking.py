"""Split document text into overlapping chunks (OpenAI File Search-style)."""

# OpenAI File Search defaults are 800 / 400 tokens. ~4 chars per token.
DEFAULT_CHUNK_CHARS = 3200


def chunk_text(
    text_value: str,
    max_chars: int = DEFAULT_CHUNK_CHARS,
    overlap: int | None = None,
) -> list[str]:
    """Split a document into overlapping chunks."""
    text_value = text_value.strip()
    if not text_value:
        return []
    if overlap is None:
        overlap = max_chars // 2
    if len(text_value) <= max_chars:
        return [text_value]

    chunks: list[str] = []
    start = 0
    while start < len(text_value):
        end = min(start + max_chars, len(text_value))
        chunk = text_value[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text_value):
            break
        start = end - overlap
    return chunks
