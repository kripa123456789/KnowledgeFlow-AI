from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="KnowledgeFlow AI", page_icon="🧠", layout="wide")

API_URL = "http://127.0.0.1:8000/upload"

st.title("KnowledgeFlow AI")
st.write("An enterprise knowledge assistant for grounded answers from your documents.")

st.info("Upload documents, ask questions, and receive answers with citations.")

uploaded_file = st.file_uploader(
    "Upload a document",
    type=["pdf", "docx", "txt"],
    help="Supported formats: PDF, DOCX, and TXT",
)

if uploaded_file is not None:
    if st.button("Upload document"):
        try:
            response = requests.post(
                API_URL,
                files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            st.success(f"Upload completed for {payload['file_name']}")
            st.session_state.setdefault("uploads", []).append(
                {
                    "file_name": payload["file_name"],
                    "file_type": payload["file_type"],
                    "file_size": payload["size_bytes"],
                    "characters": payload.get("characters", 0),
                    "pages": payload.get("pages", 1),
                    "chunk_count": payload.get("chunk_count", 0),
                    "average_chunk_size": payload.get("average_chunk_size", 0),
                    "extraction_status": payload.get("extraction_status", "unknown"),
                    "upload_time": datetime.fromisoformat(payload["uploaded_at"]).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        except requests.RequestException as exc:
            st.error(f"Upload failed: {exc}")

uploads = st.session_state.get("uploads", [])
if uploads:
    table = pd.DataFrame(uploads)
    table = table.rename(columns={"file_size": "File Size", "upload_time": "Upload Time", "extraction_status": "Extraction Status", "chunk_count": "Number of Chunks", "average_chunk_size": "Average Chunk Size"})
    st.subheader("Uploaded Documents")
    st.dataframe(table, use_container_width=True)

st.markdown("---")
st.session_state.setdefault("messages", [])

col_title, col_clear = st.columns([4, 1])
with col_title:
    st.subheader("Ask KnowledgeFlow AI")
with col_clear:
    if st.button("Clear Conversation"):
        st.session_state["messages"] = []
        st.rerun()

# Render prior conversation history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("citations"):
            st.markdown("**Sources / Citations:**")
            for cite in msg["citations"]:
                st.markdown(
                    f"- **{cite.get('filename', 'Unknown')}** (Chunk {cite.get('chunk_id', 0)}, Offsets: {cite.get('start_offset', 0)}-{cite.get('end_offset', 0)}, Score: {cite.get('score', 0.0):.4f})"
                )
        if msg.get("results"):
            with st.expander("Retrieved Context Chunks"):
                for i, hit in enumerate(msg["results"], 1):
                    payload = hit.get("payload", {})
                    score = hit.get("score", 0.0)
                    chunk_text = payload.get("chunk_text", "")
                    filename = payload.get("filename", "Unknown")
                    chunk_id = payload.get("chunk_id", 0)

                    st.markdown(f"**Chunk {i}** (Similarity Score: {score:.4f}) - Source: *{filename}* (Chunk {chunk_id})")
                    st.write(chunk_text)
                    st.caption(f"Offsets: {payload.get('start_offset', 0)} - {payload.get('end_offset', 0)}")

# Question input form
query = st.text_input("Enter your question:", key="user_question_input")
if st.button("Ask Question") and query.strip():
    try:
        backend_ask_url = API_URL.replace("/upload", "/ask")
        history_payload = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state["messages"]
            if m.get("role") in ("user", "assistant")
        ]

        response = requests.post(
            backend_ask_url,
            json={"query": query.strip(), "limit": 5, "history": history_payload},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        answer = data.get("answer", "")
        citations = data.get("citations", [])
        results = data.get("results", [])

        # Record user query and assistant response in session memory
        st.session_state["messages"].append({"role": "user", "content": query.strip()})
        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": answer,
                "citations": citations,
                "results": results,
            }
        )
        st.rerun()
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")



