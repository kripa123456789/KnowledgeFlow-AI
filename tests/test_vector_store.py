from backend.vector_store import index_chunks, initialize_collection


class FakeQdrantClient:
    def __init__(self) -> None:
        self.collections: dict[str, dict[str, object]] = {}
        self.upserts: list[tuple[str, list[dict[str, object]]]] = []

    def get_collection(self, collection_name: str) -> dict[str, object]:
        if collection_name not in self.collections:
            raise RuntimeError("missing")
        return self.collections[collection_name]

    def create_collection(self, collection_name: str, vectors_config: object) -> None:
        self.collections[collection_name] = {"vectors_config": vectors_config}

    def upsert(self, collection_name: str, points: list[dict[str, object]]) -> None:
        self.upserts.append((collection_name, points))


def test_initialize_collection_creates_collection(monkeypatch) -> None:
    fake_client = FakeQdrantClient()
    monkeypatch.setattr("backend.vector_store.get_qdrant_client", lambda: fake_client)

    initialize_collection(collection_name="test_collection")

    assert "test_collection" in fake_client.collections


def test_index_chunks_upserts_points(monkeypatch) -> None:
    fake_client = FakeQdrantClient()
    monkeypatch.setattr("backend.vector_store.get_qdrant_client", lambda: fake_client)
    monkeypatch.setattr("backend.vector_store.generate_embedding", lambda text: [0.1, 0.2, 0.3])

    count = index_chunks(
        document_id=7,
        filename="notes.txt",
        chunks=[
            {"chunk_id": 1, "text": "alpha", "character_count": 5, "start_offset": 0, "end_offset": 5},
            {"chunk_id": 2, "text": "beta", "character_count": 4, "start_offset": 5, "end_offset": 9},
        ],
        collection_name="test_collection",
    )

    assert count == 2
    assert len(fake_client.upserts) == 1
    assert fake_client.upserts[0][0] == "test_collection"
