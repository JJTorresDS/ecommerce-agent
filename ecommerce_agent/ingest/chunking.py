"""Split document text into overlapping chunks (OpenAI File Search-style)."""

from __future__ import annotations

import re

# OpenAI File Search defaults are 800 / 400 tokens. ~4 chars per token.
DEFAULT_CHUNK_CHARS = 3200

_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_HTML_HEADING_RE = re.compile(r"^<h([1-6])>(.*?)</h\1>\s*$", re.IGNORECASE)
_TAG_RE = re.compile(r"^</?h([1-6])>$", re.IGNORECASE)


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


def heading_tag_level(tag: str) -> int:
    """Map `h1` / `<h2>` to a heading level 1–6."""
    cleaned = tag.strip().lower()
    match = _TAG_RE.fullmatch(cleaned)
    if match:
        return int(match.group(1))
    if cleaned.startswith("h") and cleaned[1:].isdigit():
        level = int(cleaned[1:])
        if 1 <= level <= 6:
            return level
    raise ValueError(
        f"Invalid heading tag '{tag}'. Use h1–h6 (for example 'h1' or 'h2')."
    )


def _heading_from_line(line: str) -> tuple[int, str] | None:
    atx = _ATX_HEADING_RE.match(line)
    if atx:
        return len(atx.group(1)), atx.group(2).strip()
    html = _HTML_HEADING_RE.match(line)
    if html:
        return int(html.group(1)), html.group(2).strip()
    return None


def parse_structured_document(
    content: str,
    summary_tag: str,
    question_tag: str,
) -> tuple[str | None, list[str]]:
    """Split heading-structured text into a summary and question chunks.

    `summary_tag` / `question_tag` are heading levels (`h1`, `h2`, …).
    Text under the first summary heading is the document summary (the
    heading title is omitted). Each question heading plus the text
    beneath it becomes one chunk.
    """
    summary_level = heading_tag_level(summary_tag)
    question_level = heading_tag_level(question_tag)
    if summary_level == question_level:
        raise ValueError("summary_tag and question_tag must be different")

    summary: str | None = None
    chunks: list[str] = []
    role: str | None = None
    heading_line: str | None = None
    body_lines: list[str] = []

    def flush() -> None:
        nonlocal summary, heading_line
        body = "\n".join(body_lines).strip()
        if role == "summary":
            if summary is None and body:
                summary = body
        elif role == "question" and heading_line is not None:
            chunks.append(
                heading_line if not body else f"{heading_line}\n{body}"
            )

    for raw_line in content.splitlines():
        heading = _heading_from_line(raw_line)
        if heading is None:
            if role is not None:
                body_lines.append(raw_line)
            continue
        level, title = heading
        if level == summary_level:
            flush()
            role = "summary"
            heading_line = None
            body_lines = []
        elif level == question_level:
            flush()
            role = "question"
            heading_line = f"{'#' * level} {title}"
            body_lines = []
        elif role is not None:
            body_lines.append(raw_line)

    flush()
    return summary, chunks
