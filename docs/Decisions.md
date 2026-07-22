# Decisions Log

## Decision 001: Use FastAPI
**Reason:** FastAPI provides a modern, high-performance API layer with strong support for async workflows, clear request handling, and straightforward integration with the rest of the application.

## Decision 002: Use Streamlit
**Reason:** Streamlit offers a fast path to a polished, user-friendly interface for document upload and question workflows without introducing unnecessary frontend complexity at this stage.

## Decision 003: Use Qdrant
**Reason:** Qdrant is a purpose-built vector database that fits semantic search and retrieval use cases well, making it a strong choice for storing embeddings and supporting similarity search.

## Decision 004: Use PostgreSQL
**Reason:** PostgreSQL is a reliable relational database for storing structured metadata such as document records, upload history, and future user and organization information.

## Decision 005: Use Gemini
**Reason:** Gemini provides a strong foundation for both embedding generation and answer synthesis, allowing the product to support grounded, high-quality responses from retrieved context.
