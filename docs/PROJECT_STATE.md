# KnowledgeFlow AI — Project State & Architecture Specification

## 1. Project Overview

- **Project Name**: KnowledgeFlow AI
- **Vision**: KnowledgeFlow AI is an enterprise-grade AI knowledge assistant designed to convert internal company documentation into a centralized, reliable, searchable, and conversational knowledge base. It enables employees and teams to query organizational documents using natural language and receive grounded, accurate answers backed by source citations.
- **Purpose**: To eliminate organizational information silos and accelerate knowledge discovery by providing a secure, automated pipeline for document ingestion, text extraction, semantic indexing, grounded retrieval, and answer synthesis.
- **Goals**:
  - Provide multi-format document ingestion for PDF, DOCX, and TXT files.
  - Perform structure-preserving text extraction and sentence-boundary aware chunking.
  - Generate 768-dimensional vector embeddings using Google's official `google-genai` SDK and `gemini-embedding-001` model.
  - Store structured document and chunk metadata in PostgreSQL.
  - Store and index high-dimensional vector embeddings in Qdrant vector database.
  - Offer fast, similarity-based semantic retrieval and grounded answer synthesis (`gemini-3.6-flash`) via FastAPI backend and interactive Streamlit UI.
  - Support future retrieval-augmented generation (RAG) enhancements, prompt synthesis, source citations, multi-session conversation history, and enterprise security.

---

## 2. Current Architecture

- **Backend**: FastAPI web service running on Uvicorn ([main.py](file:///z:/KnowledgeFlow-AI/backend/main.py)). Exposes HTTP REST API endpoints:
  - `/health`: Service health check.
  - `/upload`: Ingests documents (PDF, DOCX, TXT), triggers text extraction, chunking, PostgreSQL metadata insertion, Gemini embedding generation, and Qdrant vector indexing.
  - `/search`: Receives query text, generates query vector embedding via Gemini, and retrieves top matching chunks from Qdrant.
  - `/ask`: Receives question query, retrieves vector context from Qdrant, synthesizes grounded RAG answer via `gemini-3.6-flash`, and returns response with source citations.
- **Frontend**: Interactive Streamlit web app ([app.py](file:///z:/KnowledgeFlow-AI/frontend/app.py)). Provides multi-file upload controls, real-time ingestion status tables, and an interactive "Ask KnowledgeFlow AI" interface rendering answers, citations, and expandable context chunks.
- **Database**: PostgreSQL database managed via SQLAlchemy ORM ([database.py](file:///z:/KnowledgeFlow-AI/backend/database/database.py) and [models.py](file:///z:/KnowledgeFlow-AI/backend/database/models.py)):
  - `documents` table: Stores document ID, filename, file type, page count, character count, chunk count, and upload timestamp.
  - `chunks` table: Stores chunk ID, relational foreign key to document, raw chunk text, character count, start character offset, and end character offset.
- **Vector Database**: Qdrant vector database ([vector_store.py](file:///z:/KnowledgeFlow-AI/backend/vector_store.py)). Stores 768-dimensional vectors inside the `knowledgeflow_chunks` collection using Cosine distance, storing payloads containing `document_id`, `filename`, `chunk_id`, `chunk_text`, `start_offset`, and `end_offset`.
- **Embedding Model**: `gemini-embedding-001` configured with explicit `output_dimensionality=768`. Uses `task_type="RETRIEVAL_DOCUMENT"` for document chunk indexing and `task_type="RETRIEVAL_QUERY"` for semantic query search.
- **Generation Model**: `gemini-3.6-flash` for RAG answer synthesis.
- **SDK**: Official Google Gen AI Python SDK (`google-genai`, version `>=0.1.1,<1.0`).
- **Overall Request Flow**:
  1. **Document Upload**: User uploads file in Streamlit UI ([app.py](file:///z:/KnowledgeFlow-AI/frontend/app.py)) -> HTTP POST request to FastAPI `/upload` ([main.py](file:///z:/KnowledgeFlow-AI/backend/main.py)).
  2. **File Storage & Text Extraction**: FastAPI saves raw file to `backend/uploads/` -> calls `extract_text()` ([extractor.py](file:///z:/KnowledgeFlow-AI/backend/processing/extractor.py)) to parse text and metadata -> persists extraction JSON log to `backend/data/`.
  3. **Sentence-Aware Chunking**: Raw text passed to `chunk_text()` ([chunker.py](file:///z:/KnowledgeFlow-AI/backend/processing/chunker.py)) -> splits content into ~1000 character windows with 200 character overlap, preserving sentence boundaries (`.`, `!`, `?`).
  4. **PostgreSQL Relational Storage**: Document record created in PostgreSQL `documents` table -> related chunk entries created in `chunks` table ([models.py](file:///z:/KnowledgeFlow-AI/backend/database/models.py)).
  5. **Vector Indexing**: `index_chunks()` ([vector_store.py](file:///z:/KnowledgeFlow-AI/backend/vector_store.py)) calls `generate_embedding()` via `google-genai` SDK -> upserts `PointStruct` entries containing vectors and payloads into Qdrant `knowledgeflow_chunks` collection.
  6. **RAG Question Answering Flow**: User submits question in Streamlit UI -> HTTP POST to `/ask` -> `generate_rag_answer()` retrieves context chunks via `search_similar_chunks()`, constructs strict grounding prompt, synthesizes answer using `gemini-3.6-flash`, and returns answer, inline citations, and context payloads to UI.

---

## 3. Technology Stack

- **Languages**: Python 3.10+
- **Frameworks**:
  - FastAPI (`fastapi>=0.115,<1.0`)
  - Streamlit (`streamlit>=1.37,<2.0`)
  - Uvicorn (`uvicorn[standard]>=0.30,<1.0`)
- **Libraries**:
  - `pypdf>=6.0,<7.0` (PDF document text extraction)
  - `python-docx>=1.2,<2.0` (DOCX document text extraction)
  - `pandas>=2.0,<3.0` (Frontend table rendering)
  - `pydantic` (FastAPI request and schema validation)
  - `python-dotenv>=1.0,<2.0` (Environment variable management)
  - `requests>=2.32,<3.0` & `httpx>=0.27,<1.0` (HTTP web API communication)
- **Database**: PostgreSQL (`postgresql://postgres:postgres@localhost:5432/knowledgeflow`), SQLAlchemy ORM (`sqlalchemy>=2.0,<3.0`), `psycopg2-binary>=2.9,<3.0`
- **Vector DB**: Qdrant (`qdrant-client>=1.18.0,<2.0`, running at `http://localhost:6333`, collection: `knowledgeflow_chunks`)
- **AI SDK**: Google Gen AI SDK (`google-genai>=0.1.1,<1.0`, embedding: `gemini-embedding-001`, generation: `gemini-3.6-flash`)
- **Testing**: `pytest>=8.0,<9.0` with verification test suites in `tests/` directory

---

## 4. Completed Milestones

The following features have been fully implemented, integrated, and manually verified:

- **Upload**: Endpoint `/upload` in [main.py](file:///z:/KnowledgeFlow-AI/backend/main.py) accepts PDF, DOCX, and TXT files, validates format types, and saves files to `backend/uploads/`.
- **Extraction**: Module [extractor.py](file:///z:/KnowledgeFlow-AI/backend/processing/extractor.py) extracts plain text, character counts, and page numbers for PDF, DOCX, and TXT files, saving JSON logs to `backend/data/`.
- **Chunking**: Module [chunker.py](file:///z:/KnowledgeFlow-AI/backend/processing/chunker.py) divides text into ~1000 character chunks with 200 character overlap while maintaining sentence boundary integrity.
- **PostgreSQL Storage**: Database models in [models.py](file:///z:/KnowledgeFlow-AI/backend/database/models.py) and engine setup in [database.py](file:///z:/KnowledgeFlow-AI/backend/database/database.py) store relational records for documents and chunks with offset metadata.
- **Gemini Embeddings**: Function `generate_embedding()` in [vector_store.py](file:///z:/KnowledgeFlow-AI/backend/vector_store.py) connects to `google-genai` SDK using model `gemini-embedding-001` with `output_dimensionality=768` and task-type awareness.
- **Qdrant Indexing**: Function `index_chunks()` in [vector_store.py](file:///z:/KnowledgeFlow-AI/backend/vector_store.py) initializes `knowledgeflow_chunks` collection (768 dimensions, Cosine distance) and upserts chunk vectors and payload attributes into Qdrant.
- **Semantic Search**: Endpoint `/search` in [main.py](file:///z:/KnowledgeFlow-AI/backend/main.py) receives user queries, embeds search text, calls Qdrant `query_points()`, and returns ranked similarity results.
- **`POST /ask` Endpoint**: Endpoint `/ask` in [main.py](file:///z:/KnowledgeFlow-AI/backend/main.py) accepts query payloads, invokes `generate_rag_answer()`, handles Gemini ClientErrors (429/502), and returns structured answers.
- **Grounded RAG Answer Generation**: Function `generate_rag_answer()` in [vector_store.py](file:///z:/KnowledgeFlow-AI/backend/vector_store.py) formats strict system context prompts and generates grounded answers via `gemini-3.6-flash`.
- **Citation Generation**: Preserves source metadata (`filename`, `chunk_id`, `offsets`, `score`) and formats inline citation markers (`[Source: filename, Chunk ID: chunk_id]`).
- **Streamlit Ask Interface**: Connected frontend in [app.py](file:///z:/KnowledgeFlow-AI/frontend/app.py) rendering Question, Answer, Sources/Citations, and context chunks.
- **End-to-End RAG Pipeline Manually Verified**: Complete workflow from document upload to grounded answer synthesis verified via Streamlit UI.

---

## 5. Current Working State

- **System Status**: The application is fully operational for document ingestion, processing, relational storage, vector indexing, similarity retrieval, and grounded RAG answer generation.
- **Verified Workflows**:
  - Document upload (PDF, DOCX, TXT) via Streamlit UI.
  - Text extraction, sentence-boundary chunking, PostgreSQL metadata storage, Gemini embedding generation, and Qdrant vector indexing.
  - Semantic vector search against indexed document chunks.
  - Grounded RAG answer generation with citations via `POST /ask` and Streamlit UI using `gemini-3.6-flash`.
- **Manual Verification**: Upload, semantic retrieval, and RAG answer synthesis workflows have all been manually verified through the interactive Streamlit UI ([app.py](file:///z:/KnowledgeFlow-AI/frontend/app.py)).

---

## 6. Architectural Decisions

- **Migrated from `google-generativeai` to `google-genai` SDK**:
  - *Decision*: Adopt `google-genai` (`from google import genai`) as the exclusive SDK across the application.
  - *Why*: Google deprecated legacy libraries in favor of `google-genai`, providing direct support for modern Gemini models and typed configurations.
- **Switched generation model to `gemini-3.6-flash`**:
  - *Decision*: Standardize on `gemini-3.6-flash` for RAG text generation inside `generate_rag_answer()`.
  - *Why*: `gemini-3.6-flash` offers state-of-the-art grounded generation performance, high speed, and reliability under current API availability.
- **Embeddings remain `gemini-embedding-001`**:
  - *Decision*: Retain `gemini-embedding-001` for vector embedding generation (`output_dimensionality=768`).
  - *Why*: Provides high quality vector representations optimized for retrieval tasks with task type specialization (`RETRIEVAL_DOCUMENT` vs `RETRIEVAL_QUERY`).
- **Added proper HTTP 429 handling for Gemini rate limits**:
  - *Decision*: Catch `google.genai.errors.ClientError` in `/ask` and propagate HTTP 429 for rate limit quota exhaustion instead of HTTP 500.
  - *Why*: Ensures proper HTTP status semantics, transparent error reporting in the UI, and preserves Google's retry timing messages.
- **Daily Startup Checklist established**:
  - *Decision*: Formalized system startup procedure via Docker Compose (`knowledgeflow-postgres` + `knowledgeflow-qdrant`), Uvicorn backend, and Streamlit frontend.
  - *Why*: Prevents connection errors (`psycopg2.OperationalError`) by ensuring external database services are active before running API requests.
- **Output Dimensionality = 768**:
  - *Decision*: Explicitly configure `output_dimensionality=768` in `EmbedContentConfig`.
  - *Why*: Truncating vector dimensions to 768 reduces storage requirements in Qdrant while preserving high retrieval accuracy.
- **Qdrant Collection**:
  - *Decision*: Name vector collection `knowledgeflow_chunks` with `distance="Cosine"`.
  - *Why*: Cosine similarity is optimal for normalized text embeddings generated by Gemini.
- **PostgreSQL stores metadata**:
  - *Decision*: Store document records, file stats, timestamps, and relational chunk text in PostgreSQL.
  - *Why*: Relational databases provide ACID guarantees, foreign key constraints, and structured metadata querying.
- **Qdrant stores vectors**:
  - *Decision*: Store high-dimensional float vectors and payload metadata in Qdrant vector DB.
  - *Why*: Vector databases are optimized for high-performance HNSW vector indexing and fast similarity search.

---

## 7. Development Rules

All AI assistants and developers MUST strictly enforce the following rules when working in this codebase:

1. **Diagnose before editing**: Always read error logs, tracebacks, and source code completely before proposing or applying code modifications.
2. **One feature at a time**: Focus exclusively on single, bounded features or bug fixes. Do not combine multiple unrelated changes in a single work session.
3. **Never edit more than one source file without approval**: Obtain explicit user authorization before modifying multiple code files across the workspace.
4. **Never refactor unrelated code**: Leave existing, operational code untouched unless directly required for the approved task.
5. **Never upgrade dependencies unless required**: Keep `requirements.txt` and dependency versions pinned. Do not upgrade libraries unless explicitly instructed or necessary to fix a breaking bug.
6. **Never change requirements.txt, Docker, tests, README or documentation without approval**: Critical configuration files, build scripts, test suites, and docs must not be modified without explicit consent.
7. **Always manually verify through the Streamlit UI**: Validate all backend changes by testing end-to-end user workflows in the Streamlit web app (`http://localhost:8501`).
8. **Never declare success before manual verification**: A task is complete ONLY when empirical evidence and manual verification confirm expected behavior.

---

## 8. Current Roadmap

### Completed Milestones (Version 1.0 Release)

- ✅ **Upload**: PDF, DOCX, TXT multi-format ingestion and file storage.
- ✅ **Extraction**: Plain text extraction with character & page metadata parsing.
- ✅ **Chunking**: Overlapping sentence-boundary text chunking.
- ✅ **PostgreSQL**: Relational metadata storage for documents and chunks.
- ✅ **Gemini Embeddings**: Vector embedding generation via `gemini-embedding-001` (768-dim).
- ✅ **Qdrant**: High-dimensional vector indexing and storage.
- ✅ **Semantic Search**: Vector similarity retrieval endpoint `/search`.
- ✅ **RAG Answer Generation**: Grounded answer synthesis via `gemini-3.6-flash`, `POST /ask` endpoint, inline citations, and Streamlit UI integration.
- ✅ **Conversation History**: Session-based multi-turn conversation memory, sliding window (6 messages), formatted prompt history, interactive `st.chat_message` UI, and Clear Conversation session control.
- ✅ **Streaming Responses**: Real-time token streaming via Gemini `generate_content_stream`, FastAPI `StreamingResponse` (NDJSON), and Streamlit `st.write_stream` UI rendering.
- ✅ **Prompt Optimizations**: Native `system_instruction` migration, adjacent chunk deduplication & merging, sliding window history memory.
- ✅ **Streaming Error Handling**: Pre-stream connection verification, HTTP 429 structured error responses, and NDJSON mid-stream error events.
- ✅ **Dynamic Model Config**: Environment variable configuration via `CHAT_MODEL` and `EMBEDDING_MODEL`.
- ✅ **ChatGPT-Style UI**: Modern Streamlit sidebar, sticky `st.chat_input`, staged status loaders (`st.status`), and human-friendly error banners.
- ✅ **Production Audit**: Repository cleanup, `.gitignore` & `.env.example` completeness, Docker Compose orchestration, and complete test suite verification.

---

## 9. Manual Verification Checklist

### Document Upload Verification
- [x] Start FastAPI server (`uvicorn backend.main:app --reload`) and Streamlit app (`streamlit run frontend/app.py`).
- [x] Open Streamlit UI (`http://localhost:8501`).
- [x] Select a valid sample file (PDF, DOCX, or TXT).
- [x] Click "Upload Document".
- [x] Verify success message displaying uploaded filename.
- [x] Verify document metadata row appears in Streamlit sidebar uploads summary.
- [x] Confirm file exists on disk in `backend/uploads/`.
- [x] Confirm extraction JSON output exists in `backend/data/`.
- [x] Confirm document and chunk records exist in PostgreSQL `documents` and `chunks` tables.
- [x] Confirm points exist in Qdrant collection `knowledgeflow_chunks`.

### Semantic Retrieval Verification
- [x] Enter a search query relevant to the uploaded document text.
- [x] Submit question via `st.chat_input`.
- [x] Confirm top matching context chunks are retrieved.
- [x] Confirm similarity score is displayed for each chunk.
- [x] Expand chunk view and verify chunk text corresponds to the input query.
- [x] Verify offset ranges (`start_offset`, `end_offset`) match stored metadata.

### RAG Answer Generation Verification
- [x] Submit a question requiring document context.
- [x] Verify retrieved context is correctly formatted into Gemini prompt payload.
- [x] Confirm Gemini (`gemini-3.6-flash`) generates a coherent, grounded response.
- [x] Confirm citations accurately reference source filename and chunk numbers.
- [x] Verify response handles out-of-scope queries gracefully when context is missing.

### Conversation Memory Verification
- [x] Submit a primary question in Streamlit UI.
- [x] Verify exchange appears in interactive chat view.
- [x] Submit a follow-up question referencing prior exchange.
- [x] Verify Gemini prompt receives formatted `Conversation History` and answers follow-up correctly.
- [x] Click "Clear Conversation" button and verify session chat messages reset.

### Streaming Responses & Error Handling Verification
- [x] Submit a question in Streamlit UI.
- [x] Observe live token streaming in Streamlit UI (`st.write_stream`).
- [x] Confirm citations and retrieved context chunks display cleanly after stream finishes.
- [x] Test rapid queries to trigger Gemini rate limits and verify user-friendly HTTP 429 error banners instead of abrupt connection closures.



---

## 10. AI Handoff Instructions

**CRITICAL INSTRUCTIONS FOR EVERY FUTURE AI SESSION (Antigravity, Roo Code, Claude Code, Cursor, Copilot, ChatGPT, etc.):**

Before making any changes or executing commands in this repository, you MUST follow this protocol without exception:

1. **Read `PROJECT_STATE.md` completely** before making any code or configuration changes.
2. **Summarize your understanding** of the current project state, architecture, and task scope in your initial response to the user.
3. **Explain your proposed implementation plan** step-by-step, listing affected components and files.
4. **Wait for explicit user approval** before creating, modifying, or deleting any code or file.
5. **After every code change, stop immediately and wait for manual verification** via the Streamlit UI.
6. **Never modify unrelated files**, dependencies (`requirements.txt`), test suites, Docker configs, or documentation unless explicitly requested.
