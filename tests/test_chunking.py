from backend.processing.chunker import chunk_text


def test_chunk_text_small_text() -> None:
    text = "This is a short text."

    chunks = chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == 1
    assert chunks[0]["character_count"] == len(text)
    assert chunks[0]["start_offset"] == 0
    assert chunks[0]["end_offset"] == len(text)


def test_chunk_text_large_text() -> None:
    text = "A " * 1200

    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert all(chunk["character_count"] > 0 for chunk in chunks)
    assert all(chunk["start_offset"] < chunk["end_offset"] for chunk in chunks)


def test_chunk_text_overlap_correctness() -> None:
    text = "word " * 500

    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert chunks[0]["end_offset"] > chunks[0]["start_offset"]
    assert chunks[1]["start_offset"] < chunks[0]["end_offset"]


def test_chunk_text_no_empty_chunks() -> None:
    text = "One sentence. Two sentence. Three sentence."

    chunks = chunk_text(text)

    assert all(chunk["text"] for chunk in chunks)
    assert all(chunk["character_count"] > 0 for chunk in chunks)
