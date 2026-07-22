from __future__ import annotations

import os
from typing import Any, Generator

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "knowledgeflow_chunks")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")


def get_qdrant_client() -> QdrantClient:
    """Return a configured Qdrant client."""
    return QdrantClient(url=QDRANT_URL)


def initialize_collection(collection_name: str = COLLECTION_NAME) -> None:
    """Create the Qdrant collection if it does not already exist."""
    client = get_qdrant_client()
    try:
        client.get_collection(collection_name)
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "size": 768,
                "distance": "Cosine",
            },
        )


def generate_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Generate a vector embedding for text using the Google Gen AI SDK."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=768
        )
    )

    if response.embeddings:
        values = response.embeddings[0].values
    else:
        values = []

    if not values:
        raise ValueError("Failed to generate embedding: empty response from Gemini API.")
    return list(values)


def index_chunks(document_id: int, filename: str, chunks: list[dict[str, Any]], collection_name: str = COLLECTION_NAME) -> int:
    """Store chunk embeddings and metadata in Qdrant."""
    initialize_collection(collection_name)
    client = get_qdrant_client()

    points: list[PointStruct] = []
    for chunk in chunks:
        embedding = generate_embedding(chunk["text"])
        points.append(
            PointStruct(
                id=int(chunk["chunk_id"]),
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_id": chunk["chunk_id"],
                    "chunk_text": chunk["text"],
                    "start_offset": chunk["start_offset"],
                    "end_offset": chunk["end_offset"],
                },
            )
        )

    client.upsert(collection_name=collection_name, points=points)
    return len(points)


def search_similar_chunks(query: str, limit: int = 5, collection_name: str = COLLECTION_NAME) -> list[dict[str, Any]]:
    """Search for chunks in Qdrant similar to the query."""
    client = get_qdrant_client()
    query_vector = generate_embedding(query, task_type="RETRIEVAL_QUERY")
    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
    )

    hits = []
    for hit in results.points:
        hits.append(
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
        )
    return hits


def delete_document_vectors(document_id: int, filename: str | None = None, collection_name: str = COLLECTION_NAME) -> None:
    """Delete vector points matching document_id or filename from Qdrant."""
    from qdrant_client.http import models as rest_models

    client = get_qdrant_client()
    try:
        filter_conditions = [
            rest_models.FieldCondition(
                key="document_id",
                match=rest_models.MatchValue(value=document_id)
            )
        ]
        if filename:
            filter_conditions.append(
                rest_models.FieldCondition(
                    key="filename",
                    match=rest_models.MatchValue(value=filename)
                )
            )

        client.delete(
            collection_name=collection_name,
            points_selector=rest_models.FilterSelector(
                filter=rest_models.Filter(
                    should=filter_conditions
                )
            )
        )
    except Exception:
        pass


def clear_all_vectors(collection_name: str = COLLECTION_NAME) -> None:
    """Clear all vector points from Qdrant collection."""
    client = get_qdrant_client()
    try:
        client.delete_collection(collection_name)
        initialize_collection(collection_name)
    except Exception:
        pass


SYSTEM_INSTRUCTION = (
    "You are an enterprise knowledge assistant. Answer the user's question based ONLY on the provided context chunks below.\n\n"
    "Rules:\n"
    "- Base your answer strictly on the facts present in the Context section below.\n"
    "- Do NOT use external knowledge, make assumptions, or extrapolate beyond the provided text.\n"
    '- If the context does not contain enough information to answer the question, state: "I cannot answer this question based on the provided documents."\n'
    "- Cite your sources using [Source: <filename>, Chunk: <chunk_id>] inline when presenting information."
)


def _format_context_blocks(hits: list[dict[str, Any]]) -> list[str]:
    """Merge adjacent/overlapping context chunks from the same document while removing duplicate text."""
    if not hits:
        return []

    merged_blocks = []
    i = 0
    while i < len(hits):
        hit = hits[i]
        payload = hit.get("payload", {})
        filename = payload.get("filename", "Unknown")
        chunk_ids = [payload.get("chunk_id", 0)]
        combined_text = payload.get("chunk_text", "")
        prev_end_offset = payload.get("end_offset", 0)

        j = i + 1
        while j < len(hits):
            next_payload = hits[j].get("payload", {})
            next_filename = next_payload.get("filename", "Unknown")
            next_chunk_id = next_payload.get("chunk_id", 0)
            next_start = next_payload.get("start_offset", 0)
            next_end = next_payload.get("end_offset", 0)
            next_text = next_payload.get("chunk_text", "")

            if next_filename == filename and (next_chunk_id == chunk_ids[-1] + 1 or next_start < prev_end_offset):
                overlap_len = max(0, prev_end_offset - next_start)
                non_overlap_text = next_text[overlap_len:] if overlap_len < len(next_text) else ""
                combined_text += non_overlap_text
                chunk_ids.append(next_chunk_id)
                prev_end_offset = max(prev_end_offset, next_end)
                j += 1
            else:
                break

        if len(chunk_ids) == 1:
            header = f"[Source: {filename}, Chunk ID: {chunk_ids[0]}]"
        else:
            header = f"[Source: {filename}, Chunk IDs: {chunk_ids[0]}-{chunk_ids[-1]}]"

        merged_blocks.append(f"{header}\n{combined_text}")
        i = j

    return merged_blocks


def generate_rag_answer(
    query: str,
    limit: int = 5,
    collection_name: str = COLLECTION_NAME,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Retrieve matching document chunks and synthesize a grounded answer using Gemini LLM."""
    hits = search_similar_chunks(query=query, limit=limit, collection_name=collection_name)

    if not hits:
        return {
            "query": query,
            "answer": "I cannot answer this question based on the provided documents.",
            "citations": [],
            "results": [],
        }

    citations = []
    for hit in hits:
        payload = hit.get("payload", {})
        citations.append(
            {
                "filename": payload.get("filename", "Unknown"),
                "chunk_id": payload.get("chunk_id", 0),
                "start_offset": payload.get("start_offset", 0),
                "end_offset": payload.get("end_offset", 0),
                "score": hit.get("score", 0.0),
            }
        )

    context_blocks = _format_context_blocks(hits)
    formatted_context = "\n\n---\n\n".join(context_blocks)

    formatted_history = ""
    if history:
        recent_history = history[-6:]
        history_lines = []
        for msg in recent_history:
            role_label = "User" if msg.get("role") in ("user", "human") else "Assistant"
            history_lines.append(f"{role_label}: {msg.get('content', '')}")
        formatted_history = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

    prompt = f"{formatted_history}Context:\n{formatted_context}\n\nQuestion: {query}"

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION
    )
    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=config,
    )

    answer_text = response.text.strip() if response.text else "I cannot answer this question based on the provided documents."

    return {
        "query": query,
        "answer": answer_text,
        "citations": citations,
        "results": hits,
    }


def init_rag_stream(
    query: str,
    limit: int = 5,
    collection_name: str = COLLECTION_NAME,
    history: list[dict[str, str]] | None = None,
) -> Generator[str, None, None]:
    """Perform context retrieval and establish Gemini streaming connection before committing HTTP response."""
    import json

    hits = search_similar_chunks(query=query, limit=limit, collection_name=collection_name)

    if not hits:
        def empty_generator():
            yield json.dumps({"type": "metadata", "citations": [], "results": []}) + "\n"
            yield json.dumps({"type": "token", "text": "I cannot answer this question based on the provided documents."}) + "\n"
        return empty_generator()

    citations = []
    for hit in hits:
        payload = hit.get("payload", {})
        citations.append(
            {
                "filename": payload.get("filename", "Unknown"),
                "chunk_id": payload.get("chunk_id", 0),
                "start_offset": payload.get("start_offset", 0),
                "end_offset": payload.get("end_offset", 0),
                "score": hit.get("score", 0.0),
            }
        )

    context_blocks = _format_context_blocks(hits)
    formatted_context = "\n\n---\n\n".join(context_blocks)

    formatted_history = ""
    if history:
        recent_history = history[-6:]
        history_lines = []
        for msg in recent_history:
            role_label = "User" if msg.get("role") in ("user", "human") else "Assistant"
            history_lines.append(f"{role_label}: {msg.get('content', '')}")
        formatted_history = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

    prompt = f"{formatted_history}Context:\n{formatted_context}\n\nQuestion: {query}"

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION
    )

    # Establish API stream connection synchronously BEFORE Returning generator
    response_stream = client.models.generate_content_stream(
        model=CHAT_MODEL,
        contents=prompt,
        config=config,
    )

    stream_iter = iter(response_stream)
    # Test first chunk pull to catch pre-stream ClientErrors (HTTP 429/500) before HTTP headers are sent
    first_chunk = next(stream_iter, None)

    def active_generator():
        # Connection successfully established: emit metadata payload first
        yield json.dumps({"type": "metadata", "citations": citations, "results": hits}) + "\n"

        if first_chunk and first_chunk.text:
            yield json.dumps({"type": "token", "text": first_chunk.text}) + "\n"

        # Stream remaining chunks with mid-stream error guard
        try:
            for chunk in stream_iter:
                if chunk.text:
                    yield json.dumps({"type": "token", "text": chunk.text}) + "\n"
        except Exception as exc:
            err_msg = "Gemini API rate limit reached. Please retry in a few seconds." if "429" in str(exc) else f"Streaming error: {exc}"
            yield json.dumps({"type": "error", "message": err_msg}) + "\n"

    return active_generator()


def stream_rag_answer(
    query: str,
    limit: int = 5,
    collection_name: str = COLLECTION_NAME,
    history: list[dict[str, str]] | None = None,
) -> Generator[str, None, None]:
    """Stream grounded answer tokens and metadata using Gemini generate_content_stream API."""
    gen = init_rag_stream(query=query, limit=limit, collection_name=collection_name, history=history)
    yield from gen



