from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "knowledgeflow_chunks")


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
        model="gemini-embedding-001",
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

    context_blocks = []
    citations = []
    for hit in hits:
        payload = hit.get("payload", {})
        filename = payload.get("filename", "Unknown")
        chunk_id = payload.get("chunk_id", 0)
        chunk_text = payload.get("chunk_text", "")
        start_offset = payload.get("start_offset", 0)
        end_offset = payload.get("end_offset", 0)
        score = hit.get("score", 0.0)

        context_blocks.append(f"[Source: {filename}, Chunk ID: {chunk_id}]\n{chunk_text}")
        citations.append(
            {
                "filename": filename,
                "chunk_id": chunk_id,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "score": score,
            }
        )

    formatted_context = "\n\n---\n\n".join(context_blocks)

    formatted_history = ""
    if history:
        history_lines = []
        for msg in history:
            role_label = "User" if msg.get("role") in ("user", "human") else "Assistant"
            history_lines.append(f"{role_label}: {msg.get('content', '')}")
        formatted_history = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

    prompt = (
        "You are an enterprise knowledge assistant. Answer the user's question based ONLY on the provided context chunks below.\n\n"
        "Rules:\n"
        "- Base your answer strictly on the facts present in the Context section below.\n"
        "- Do NOT use external knowledge, make assumptions, or extrapolate beyond the provided text.\n"
        '- If the context does not contain enough information to answer the question, state: "I cannot answer this question based on the provided documents."\n'
        "- Cite your sources using [Source: <filename>, Chunk: <chunk_id>] inline when presenting information.\n\n"
        f"{formatted_history}"
        f"Context:\n{formatted_context}\n\n"
        f"Question: {query}"
    )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")

    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    answer_text = response.text.strip() if response.text else "I cannot answer this question based on the provided documents."

    return {
        "query": query,
        "answer": answer_text,
        "citations": citations,
        "results": hits,
    }


