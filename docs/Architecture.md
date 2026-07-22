# Architecture

KnowledgeFlow AI is structured as a modular application with a simple, production-friendly flow from document upload to answer generation.

## High-Level Flow

```text
Frontend (Streamlit)
        |
        v
FastAPI Backend
        |
        v
Document Upload
        |
        v
Text Extraction
        |
        v
Chunking
        |
        v
Embeddings
        |
        v
Qdrant
        |
        v
Gemini
        |
        v
Answer Generation
        |
        v
Citations
```

## Components

### Frontend
The user interface is built with Streamlit. It provides a simple experience for uploading documents, viewing upload history, and asking questions.

### Backend
The backend is implemented with FastAPI. It exposes API endpoints for document upload and future retrieval and answer-generation workflows.

### Document Upload
Uploaded files are stored locally in the backend upload directory before the next processing steps are introduced.

### Text Extraction
The next stage will extract text from uploaded PDF, DOCX, and TXT files so the content can be processed further.

### Chunking
Extracted text will be split into smaller chunks to improve retrieval accuracy and context handling.

### Embeddings
Each text chunk will be converted into embeddings using the Gemini embedding API.

### Qdrant
Embeddings and associated metadata will be stored in Qdrant for vector search.

### Gemini
Gemini will be used to generate answers from retrieved context and to support future conversational workflows.

### Answer Generation
The application will retrieve the most relevant chunks and ask Gemini to generate a grounded answer based on them.

### Citations
Answers will include citations back to the source documents and relevant chunks so users can verify the response.
