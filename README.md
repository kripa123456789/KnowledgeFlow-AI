# 🧠 KnowledgeFlow AI

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Streamlit-1.37+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Qdrant-v1.13-DC382D?style=for-the-badge&logo=qdrant&logoColor=white" alt="Qdrant" />
  <img src="https://img.shields.io/badge/Google%20Gemini-Flash%203.6-8E75B2?style=for-the-badge&logo=google&logoColor=white" alt="Google Gemini" />
  <img src="https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Pytest-18%20Passed-464646?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License" />
</p>

KnowledgeFlow AI is an enterprise-grade **Retrieval-Augmented Generation (RAG)** knowledge assistant designed to convert internal company documentation into a secure, conversational, and citation-backed source of truth. Built with a high-performance Python tech stack (**FastAPI**, **Streamlit**, **Qdrant**, **PostgreSQL**, and **Google Gemini API**), KnowledgeFlow AI enables employees to upload multi-format documents, ask natural language questions, and receive grounded answers with exact source citations and real-time token streaming.

---

## ✨ Capability & Feature Matrix

| Feature | Technical Implementation | Enterprise Benefit |
| :--- | :--- | :--- |
| **Multi-Format Ingestion** | `pypdf`, `python-docx`, `txt` extractors | Ingest contracts, resumes, PRDs, and internal notes effortlessly |
| **Sentence-Aware Chunking** | Overlapping windowing (~1000 char window / 200 overlap) | Preserves semantic integrity across sentence boundaries |
| **768-Dim Vector Embeddings** | Google Gen AI SDK (`gemini-embedding-001`) | High-accuracy document chunk representations optimized for retrieval |
| **HNSW Vector Database** | Qdrant (`v1.13.0`) HNSW Cosine Indexing | Sub-millisecond similarity search across indexed document spaces |
| **Relational Metadata** | PostgreSQL (`v17`) & SQLAlchemy ORM | ACID-compliant tracking of documents, page counts, and character offsets |
| **Grounded Answer Synthesis** | `gemini-3.6-flash` + Native System Instruction | Grounded, accurate answers that strictly eliminate hallucinations |
| **Expandable Citation Cards** | Interactive Streamlit cards with percentage match | Transparent citation linking answers directly back to exact source text |
| **Real-Time Token Streaming** | FastAPI `StreamingResponse` (NDJSON) + `st.write_stream` | Instant response feedback with sub-second Time-To-First-Token (~0.8s) |
| **Resilient Error Handling** | Pre-stream socket guard & HTTP 429 rate limit handlers | Prevents socket drops and presents human-friendly status banners |
| **Full Document Management** | Delete document, refresh list, bulk delete endpoints | Complete control over stored files, PostgreSQL metadata, and Qdrant vectors |

---

## 🛠️ Architecture & Pipeline Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Employee / User
    participant UI as Streamlit UI
    participant Backend as FastAPI Server
    participant PG as PostgreSQL DB
    participant Qdrant as Qdrant Vector DB
    participant Gemini as Google Gemini API

    rect rgb(240, 248, 255)
    note right of User: Document Ingestion Pipeline
    User->>UI: Upload File (PDF/DOCX/TXT)
    UI->>Backend: POST /upload
    Backend->>Backend: Extract Text & Sentence Chunking
    Backend->>PG: Save Document & Chunk Metadata
    Backend->>Gemini: Generate 768-Dim Vector Embeddings
    Gemini-->>Backend: Return Vector Embeddings
    Backend->>Qdrant: Upsert Vector Points (Cosine)
    Backend-->>UI: Return Ingestion Summary
    end

    rect rgb(255, 250, 240)
    note right of User: RAG Query & Streaming Pipeline
    User->>UI: Submit Question via st.chat_input
    UI->>Backend: POST /ask (query + conversation history)
    Backend->>Gemini: Embed Query Vector
    Gemini-->>Backend: Return Query Vector
    Backend->>Qdrant: Search Similar Chunks (Top-K)
    Qdrant-->>Backend: Return Top Matching Chunks
    Backend->>Backend: Merge Adjacent Chunks & Strip Overlap
    Backend->>Gemini: Stream Answer (System Instruction + Context)
    Gemini-->>Backend: Response Tokens Stream (NDJSON)
    Backend-->>UI: Live Stream Tokens & Citation Cards
    end
```

---

## 📸 Visual Showcase

Explore screenshot walkthroughs and asset guidelines in [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md).

| ChatGPT-Style Chat Interface | Professional Citation Cards |
| :---: | :---: |
| ![Chat Interface](docs/screenshots/chat_interface.png) | ![Citation Cards](docs/screenshots/citation_cards.png) |

| Sidebar Document Management | Real-Time Upload Progress |
| :---: | :---: |
| ![Document Management](docs/screenshots/document_management.png) | ![Upload Progress](docs/screenshots/upload_progress.png) |

---

## 💻 Tech Stack & Dependencies

- **Backend**: Python 3.10+, FastAPI, Uvicorn, SQLAlchemy ORM, Pydantic
- **Frontend**: Streamlit, Pandas
- **Vector Database**: Qdrant Vector Database (`v1.13.0`)
- **Relational Database**: PostgreSQL (`v17`)
- **AI Engine**: Google Gen AI SDK (`google-genai`)
- **AI Models**: `gemini-3.6-flash` (RAG Generation), `gemini-embedding-001` (Embeddings)
- **Infrastructure**: Docker & Docker Compose

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Docker Desktop installed and running.
- Python 3.10+ installed.
- A Google Gemini API Key ([Get API Key](https://ai.google.dev/)).

### 2. Environment Setup
Clone the repository and set up environment variables:
```bash
cp .env.example .env
```
Edit `.env` and set your `GEMINI_API_KEY`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
CHAT_MODEL=gemini-3.6-flash
EMBEDDING_MODEL=gemini-embedding-001
```

### 3. Launch Docker Infrastructure
Start PostgreSQL and Qdrant vector database:
```bash
docker compose up -d
```
- **PostgreSQL**: `localhost:5432`
- **Qdrant Dashboard**: `http://localhost:6333/dashboard`

### 4. Install Dependencies
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 5. Launch Application
Terminal 1 (Backend Server):
```bash
uvicorn backend.main:app --reload
```

Terminal 2 (Streamlit UI):
```bash
streamlit run frontend/app.py
```
Open your browser to `http://localhost:8501`.

---

## 🧪 Testing

Run the automated Pytest suite:
```bash
pytest tests/
```

---

## 📚 Technical Documentation

- [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) — Comprehensive technical architecture & current state.
- [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md) — Visual showcase & screenshot asset guide.
- [docs/Vision.md](docs/Vision.md) — Product vision and goals.
- [docs/Architecture.md](docs/Architecture.md) — Technical component design.
- [docs/Decisions.md](docs/Decisions.md) — Architectural Decision Records (ADR).
