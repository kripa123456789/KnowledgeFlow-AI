import io
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_list_documents_endpoint():
    """Verify GET /documents returns a list of documents."""
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "count" in data
    assert isinstance(data["documents"], list)


def test_document_lifecycle_upload_list_delete():
    """Verify document upload, listing in GET /documents, and deletion via DELETE /documents/{id}."""
    file_content = b"Document lifecycle management test text content for KnowledgeFlow AI."
    file_name = "test_lifecycle_doc.txt"

    # 1. Upload document
    upload_res = client.post(
        "/upload",
        files={"file": (file_name, io.BytesIO(file_content), "text/plain")},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["file_name"] == file_name

    # 2. List documents
    list_res = client.get("/documents")
    assert list_res.status_code == 200
    docs = list_res.json()["documents"]
    matched_doc = next((d for d in docs if d["file_name"] == file_name), None)
    assert matched_doc is not None
    doc_id = matched_doc["id"]
    assert matched_doc["chunk_count"] > 0

    # 3. Delete single document
    del_res = client.delete(f"/documents/{doc_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["document_id"] == doc_id

    # 4. Verify document is no longer listed
    list_res_after = client.get("/documents")
    docs_after = list_res_after.json()["documents"]
    assert not any(d["id"] == doc_id for d in docs_after)


def test_delete_all_documents_endpoint():
    """Verify DELETE /documents clears all stored documents."""
    response = client.delete("/documents")
    assert response.status_code == 200
    assert "message" in response.json()

    list_res = client.get("/documents")
    assert list_res.status_code == 200
    assert list_res.json()["count"] == 0
