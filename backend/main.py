from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.database.database import SessionLocal, init_db
from backend.database.models import Chunk, Document
from backend.processing.chunker import chunk_text
from backend.processing.extractor import extract_text, save_extraction_result
from backend.vector_store import (
    clear_all_vectors,
    delete_document_vectors,
    generate_rag_answer,
    index_chunks,
    init_rag_stream,
    search_similar_chunks,
    stream_rag_answer,
)

app = FastAPI(title="KnowledgeFlow AI API", version="0.1.0")

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
DATA_DIR = Path(__file__).resolve().parent / "data"
SUPPORTED_TYPES = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "txt": "text/plain"}

init_db()


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok"}


@app.get("/documents")
def list_documents() -> dict[str, object]:
    """List all uploaded document metadata records from PostgreSQL."""
    db = SessionLocal()
    try:
        docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
        result = []
        for doc in docs:
            filepath = UPLOAD_DIR / doc.filename
            size_bytes = filepath.stat().st_size if filepath.exists() else 0
            result.append(
                {
                    "id": doc.id,
                    "file_name": doc.filename,
                    "file_type": doc.file_type,
                    "pages": doc.pages,
                    "characters": doc.characters,
                    "chunk_count": doc.chunk_count,
                    "size_bytes": size_bytes,
                    "uploaded_at": doc.uploaded_at.isoformat(),
                }
            )
        return {"documents": result, "count": len(result)}
    finally:
        db.close()


@app.delete("/documents/{document_id}")
def delete_document(document_id: int) -> dict[str, object]:
    """Delete a document, its chunks from PostgreSQL, vectors from Qdrant, and files from disk."""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        filename = doc.filename

        # 1. Delete vectors from Qdrant
        delete_document_vectors(document_id=doc.id, filename=filename)

        # 2. Delete relational records from PostgreSQL
        db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
        db.delete(doc)
        db.commit()

        # 3. Delete raw file and extraction JSON from disk
        raw_path = UPLOAD_DIR / filename
        if raw_path.exists():
            raw_path.unlink()

        json_path = DATA_DIR / f"{filename}.json"
        if json_path.exists():
            json_path.unlink()

        return {"message": f"Successfully deleted document '{filename}'", "document_id": document_id}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


@app.delete("/documents")
def delete_all_documents() -> dict[str, object]:
    """Delete all documents, chunks, vectors, and disk files."""
    db = SessionLocal()
    try:
        # 1. Clear all vectors from Qdrant
        clear_all_vectors()

        # 2. Clear all relational records from PostgreSQL
        db.query(Chunk).delete()
        db.query(Document).delete()
        db.commit()

        # 3. Delete files from disk preserving .gitkeep
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.name != ".gitkeep" and file_path.is_file():
                file_path.unlink()

        for file_path in DATA_DIR.glob("*"):
            if file_path.name != ".gitkeep" and file_path.is_file():
                file_path.unlink()

        return {"message": "Successfully deleted all documents and vector collections"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


@app.post("/upload")
def upload_document(file: Annotated[UploadFile, File(...)]) -> dict[str, object]:
    """Store an uploaded document, extract its text, and return metadata."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    file_name = file.filename or "uploaded_file"
    file_suffix = Path(file_name).suffix.lower().lstrip(".")
    if file_suffix not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a PDF, DOCX, or TXT file.")

    destination = UPLOAD_DIR / file_name
    contents = file.file.read()
    destination.write_bytes(contents)

    extraction_result = extract_text(destination)
    chunks = chunk_text(extraction_result.get("text", "")) if extraction_result.get("success") else []
    extraction_payload = {
        "filename": file_name,
        "text": extraction_result.get("text", ""),
        "pages": extraction_result.get("pages", 1),
        "characters": extraction_result.get("characters", 0),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "extraction_status": "success" if extraction_result.get("success") else "failed",
        "error": extraction_result.get("error"),
        "chunks": chunks,
        "chunk_count": len(chunks),
        "average_chunk_size": round(sum(chunk["character_count"] for chunk in chunks) / len(chunks), 2) if chunks else 0,
    }
    save_extraction_result(destination, extraction_payload, DATA_DIR)

    db = SessionLocal()
    try:
        document = Document(
            filename=file_name,
            file_type=file_suffix,
            pages=extraction_payload["pages"],
            characters=extraction_payload["characters"],
            chunk_count=extraction_payload["chunk_count"],
            uploaded_at=datetime.now(timezone.utc),
        )
        db.add(document)
        db.flush()

        for chunk in chunks:
            db.add(
                Chunk(
                    document_id=document.id,
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    character_count=chunk["character_count"],
                    start_offset=chunk["start_offset"],
                    end_offset=chunk["end_offset"],
                )
            )

        vector_count = index_chunks(document_id=document.id, filename=file_name, chunks=chunks)
        extraction_payload["vector_count"] = vector_count
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()

    return {
        "file_name": file_name,
        "file_type": file_suffix,
        "size_bytes": len(contents),
        "stored_path": str(destination),
        "uploaded_at": extraction_payload["uploaded_at"],
        "pages": extraction_payload["pages"],
        "characters": extraction_payload["characters"],
        "extraction_status": extraction_payload["extraction_status"],
        "chunk_count": extraction_payload["chunk_count"],
        "average_chunk_size": extraction_payload["average_chunk_size"],
    }


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The query string to search for")
    limit: int = Field(5, ge=1, le=50, description="The maximum number of results to return")


@app.post("/search")
def search_chunks(request: SearchRequest) -> dict[str, object]:
    """Retrieve top matching chunks from Qdrant vector database."""
    try:
        results = search_similar_chunks(query=request.query, limit=request.limit)
        return {"query": request.query, "results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


from google.genai.errors import ClientError

class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The query string to ask")
    limit: int = Field(5, ge=1, le=50, description="The maximum number of context chunks to retrieve")
    history: list[dict[str, str]] = Field(default_factory=list, description="Previous conversation message objects")


@app.post("/ask")
def ask_rag_question(request: AskRequest):
    """Stream a grounded answer based on retrieved vector context."""
    try:
        generator = init_rag_stream(
            query=request.query,
            limit=request.limit,
            history=request.history,
        )
        return StreamingResponse(generator, media_type="application/x-ndjson")
    except ClientError as exc:
        code = getattr(exc, "code", None)
        if code == 429 or "429" in str(exc):
            raise HTTPException(status_code=429, detail=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))




