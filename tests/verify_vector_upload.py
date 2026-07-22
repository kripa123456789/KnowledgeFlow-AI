import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
file_path = Path("tests/sample_vector_upload.txt")
file_path.write_bytes(b"Qdrant verification text for embedding pipeline")
with file_path.open("rb") as handle:
    response = client.post(
        "/upload",
        files={"file": ("sample_vector_upload.txt", handle, "text/plain")},
    )

print(response.status_code)
print(response.json())
