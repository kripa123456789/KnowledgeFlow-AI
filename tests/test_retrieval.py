from __future__ import annotations

from typing import Any
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.vector_store import search_similar_chunks


class FakeScoredPoint:
    def __init__(self, id: int, score: float, payload: dict[str, Any]) -> None:
        self.id = id
        self.score = score
        self.payload = payload


class FakeQueryResponse:
    def __init__(self, points: list[FakeScoredPoint]) -> None:
        self.points = points


class FakeQdrantClient:
    def __init__(self, search_results: list[FakeScoredPoint]) -> None:
        self.search_results = search_results

    def query_points(self, collection_name: str, query: list[float], limit: int) -> FakeQueryResponse:
        return FakeQueryResponse(self.search_results[:limit])


def test_search_similar_chunks_calls_qdrant(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_results = [
        FakeScoredPoint(1, 0.95, {"chunk_text": "hello"}),
        FakeScoredPoint(2, 0.85, {"chunk_text": "world"}),
    ]
    fake_client = FakeQdrantClient(fake_results)

    monkeypatch.setattr("backend.vector_store.get_qdrant_client", lambda: fake_client)
    monkeypatch.setattr("backend.vector_store.generate_embedding", lambda text, task_type: [0.1] * 768)

    hits = search_similar_chunks("test query", limit=2)

    assert len(hits) == 2
    assert hits[0]["id"] == 1
    assert hits[0]["score"] == 0.95
    assert hits[0]["payload"]["chunk_text"] == "hello"


def test_search_endpoint_returns_results(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_results = [
        {"id": 1, "score": 0.95, "payload": {"chunk_text": "hello"}},
    ]
    monkeypatch.setattr("backend.main.search_similar_chunks", lambda query, limit: fake_results)

    client = TestClient(app)
    response = client.post("/search", json={"query": "test query", "limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "test query"
    assert len(payload["results"]) == 1
    assert payload["results"][0]["id"] == 1
