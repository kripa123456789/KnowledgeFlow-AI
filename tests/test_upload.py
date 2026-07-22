from pathlib import Path

from fastapi.testclient import TestClient

from backend import main


client = TestClient(main.app)


def test_upload_endpoint_saves_file_and_returns_metadata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("backend.vector_store.generate_embedding", lambda text, task_type="RETRIEVAL_DOCUMENT": [0.1] * 768)

    response = client.post(
        "/upload",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "notes.txt"
    assert payload["file_type"] == "txt"
    assert payload["size_bytes"] > 0
    assert payload["stored_path"].endswith("notes.txt")

    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == b"hello world"


def test_upload_endpoint_rejects_unsupported_extension(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/upload",
        files={"file": ("notes.csv", b"data", "text/csv")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
