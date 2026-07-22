from __future__ import annotations

import re
from typing import Any


CHUNK_SIZE = 1000
OVERLAP = 200


def _sentence_boundaries(text: str) -> list[int]:
    """Return sentence boundary positions for the provided text."""
    return [match.end() for match in re.finditer(r"(?<=[.!?])(?:\s+|$)", text)]


def chunk_text(text: str) -> list[dict[str, Any]]:
    """Split text into overlapping chunks while preserving sentence boundaries when possible."""
    if not text or not text.strip():
        return []

    normalized = text.strip()
    boundaries = _sentence_boundaries(normalized)
    chunks: list[dict[str, Any]] = []
    start = 0

    while start < len(normalized):
        end = min(len(normalized), start + CHUNK_SIZE)
        boundary = max((value for value in boundaries if start < value <= end), default=None)
        if boundary is not None:
            end = boundary

        chunk_text_content = normalized[start:end].strip()
        if not chunk_text_content:
            start = end if end > start else start + 1
            continue

        chunks.append(
            {
                "chunk_id": len(chunks) + 1,
                "text": chunk_text_content,
                "character_count": len(chunk_text_content),
                "start_offset": start,
                "end_offset": end,
            }
        )

        if end >= len(normalized):
            break

        next_start = max(0, end - OVERLAP)
        if boundaries:
            boundary_before_start = max(
                (value for value in boundaries if start < value <= next_start),
                default=None,
            )
            if boundary_before_start is not None:
                next_start = boundary_before_start

        if next_start <= start:
            next_start = end

        # Align next_start to word boundary if it lands in the middle of a word
        while next_start > start and next_start < len(normalized) and normalized[next_start - 1].isalnum() and normalized[next_start].isalnum():
            next_start -= 1

        start = max(start + 1, next_start)

    return chunks
