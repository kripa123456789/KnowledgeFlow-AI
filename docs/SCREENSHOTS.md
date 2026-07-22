# 🖼️ KnowledgeFlow AI — Interface & Portfolio Showcase Guide

This guide provides visual walk-throughs and screenshot asset guidelines for KnowledgeFlow AI's Version 1.0 release.

---

## 📸 Key Application Screenshots

### 1. ChatGPT-Style Conversational Interface
![Chat Interface](file:///z:/KnowledgeFlow-AI/docs/screenshots/chat_interface.png)
*Description: Persistent chat interface featuring sticky input box, staged status loader (`st.status`), live token streaming, and expander context inspections.*

---

### 2. Managed Document Sidebar Cards
![Sidebar Document Management](file:///z:/KnowledgeFlow-AI/docs/screenshots/document_management.png)
*Description: Sidebar document panel displaying uploaded files as clean cards with upload timestamp, size (KB), page count, chunk count, single document deletion, and bulk reset actions.*

---

### 3. Professional Expandable Citation Cards
![Citation Cards](file:///z:/KnowledgeFlow-AI/docs/screenshots/citation_cards.png)
*Description: Expandable citation cards displaying source document filename, chunk ID, exact similarity match percentage (`85.24%`), character offset range, and chunk content preview box.*

---

### 4. Real-Time Upload Progress Experience
![Real-Time Upload Progress](file:///z:/KnowledgeFlow-AI/docs/screenshots/upload_progress.png)
*Description: Multi-stage progress loader displaying sequential ingestion steps (Uploading → Extracting → Chunking → Embeddings → Database → Qdrant).*

---

## 🎨 Asset File Structure

Place high-resolution PNG screenshots into the `docs/screenshots/` folder matching the filenames below:

```text
docs/screenshots/
├── chat_interface.png        # Main chat conversation & live streaming view
├── document_management.png   # Managed document cards in Streamlit sidebar
├── citation_cards.png        # Expandable source citation card view
└── upload_progress.png       # Real-time multi-stage ingestion loader
```
