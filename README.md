# KnowledgeFlow AI

KnowledgeFlow AI is an enterprise knowledge assistant built to help organizations turn internal documents into a conversational, citation-backed source of truth. Employees can upload documents, ask questions in natural language, and receive answers grounded in the uploaded content.

## Project Overview

KnowledgeFlow AI is being built as a production-style SaaS application for internal knowledge access. The initial version focuses on document upload and storage, with future iterations adding text extraction, semantic retrieval, embeddings, and AI-generated answers with citations.

## Features

Current capabilities:
- Upload PDF, DOCX, and TXT files
- Save uploaded documents to the backend upload directory
- Extract readable text immediately after upload
- Split extracted text into overlapping chunks
- Persist document and chunk metadata in PostgreSQL via SQLAlchemy
- Keep JSON output as a debug artifact in the backend data directory
- View upload history in the Streamlit interface with extraction and chunking metrics

Planned capabilities:
- Text extraction from uploaded documents
- Document chunking
- Embedding generation
- Vector search with Qdrant
- Grounded answers with Gemini and citations
- Conversation history and multi-user expansion

## Tech Stack

- Python
- FastAPI
- Streamlit
- Gemini API
- Qdrant
- PostgreSQL
- SQLAlchemy
- Docker
- python-dotenv

## Architecture

The system is organized around a simple pipeline:

1. Streamlit frontend for user interaction
2. FastAPI backend for request handling
3. Local document storage for uploaded files
4. Future extraction, chunking, embedding, retrieval, and answer-generation layers

For more detail, see [docs/Architecture.md](docs/Architecture.md).

## Current Status

The project has successfully completed the baseline RAG ingestion pipeline. The following milestones are fully implemented and verified:
- **File Upload**: Accept supported file uploads and store them on disk.
- **PDF/DOCX/TXT Extraction**: Extract readable text immediately after upload.
- **Text Chunking**: Split extracted text into overlapping chunks while preserving sentence boundaries.
- **PostgreSQL Metadata Storage**: Save document and chunk metadata in PostgreSQL.
- **Gemini Embedding Generation**: Generate 768-dimension vector embeddings using the Gemini Embedding API.
- **Qdrant Vector Storage**: Index chunk embeddings in Qdrant for semantic search.

## Project Structure

```text
backend/
frontend/
docs/
tests/
docker/
```

## How to Run

### Start infrastructure with Docker

1. Ensure Docker Desktop is running.
2. Start the database and vector services:
   `docker compose up -d`
3. Stop the containers when needed:
   `docker compose down`
4. Connect to PostgreSQL:
   `docker exec -it knowledgeflow-postgres psql -U postgres -d knowledgeflow`
5. Access Qdrant:
   `http://localhost:6333/dashboard`

### Start the application locally

1. Create and activate a Python virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Start the backend:
   `uvicorn backend.main:app --reload`
4. Start the frontend:
   `streamlit run frontend/app.py`

## Roadmap

The implementation plan is tracked in [docs/Roadmap.md](docs/Roadmap.md).

## Documentation

- [docs/Vision.md](docs/Vision.md)
- [docs/Architecture.md](docs/Architecture.md)
- [docs/Roadmap.md](docs/Roadmap.md)
- [docs/Decisions.md](docs/Decisions.md)
- [docs/Progress.md](docs/Progress.md)
