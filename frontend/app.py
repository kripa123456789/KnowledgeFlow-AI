import concurrent.futures
from datetime import datetime, timedelta, timezone
import json
import time

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="KnowledgeFlow AI", page_icon="🧠", layout="wide")

API_URL = "http://127.0.0.1:8000/upload"
DOCUMENTS_API_URL = "http://127.0.0.1:8000/documents"

# Session state initialization for widget keys and toast notifications
st.session_state.setdefault("uploader_key", 0)

if "toast_msg" in st.session_state:
    st.toast(st.session_state.pop("toast_msg"))


def perform_upload(file_name, file_bytes, file_type):
    """Execute upload POST request in worker thread."""
    return requests.post(
        API_URL,
        files={"file": (file_name, file_bytes, file_type or "application/octet-stream")},
        timeout=60,
    )


def format_error_message(exc: Exception) -> str:
    """Format technical exceptions into concise, user-friendly messages."""
    err_str = str(exc)
    if isinstance(exc, requests.RequestException) and exc.response is not None:
        status_code = exc.response.status_code
        if status_code == 429:
            return "⏳ The AI model is currently experiencing high demand. Please wait a few seconds and try again."
        elif status_code in (500, 502, 503, 504):
            return "⚠️ The backend server encountered a temporary issue. Please try again shortly."
        try:
            detail = exc.response.json().get("detail", "")
            if "RESOURCE_EXHAUSTED" in detail or "429" in detail:
                return "⏳ Rate limit reached. Please wait a few seconds before asking your next question."
        except Exception:
            pass
    if "Connection refused" in err_str or "Failed to establish a new connection" in err_str:
        return "🔌 Unable to connect to KnowledgeFlow AI backend. Please check that the server is running."
    return f"❌ Request error: {err_str}"


def format_local_timestamp(iso_str: str) -> str:
    """Convert UTC ISO timestamp string to Asia/Kolkata (UTC+5:30) local format."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        local_dt = dt.astimezone(ist_tz)
        return local_dt.strftime("%Y-%m-%d %I:%M %p IST")
    except Exception:
        return iso_str


def fetch_documents():
    """Fetch list of uploaded documents from backend API."""
    try:
        res = requests.get(DOCUMENTS_API_URL, timeout=10)
        res.raise_for_status()
        return res.json().get("documents", [])
    except Exception:
        return []


# --- SIDEBAR: Document Uploads & Controls ---
with st.sidebar:
    st.title("🧠 KnowledgeFlow AI")
    st.caption("Enterprise RAG Knowledge Assistant")
    st.markdown("---")

    st.subheader("📁 Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload document(s)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['uploader_key']}",
        help="Supported formats: PDF, DOCX, and TXT",
    )

    if uploaded_files:
        if st.button("📤 Upload Selected Documents", use_container_width=True):
            with st.status("📁 Ingesting Documents...", expanded=True) as upload_status:
                total_files = len(uploaded_files)
                successful_uploads = []

                for idx, up_file in enumerate(uploaded_files, 1):
                    file_name = up_file.name
                    file_bytes = up_file.getvalue()
                    file_type = up_file.type

                    upload_status.update(label=f"📁 Processing File {idx}/{total_files}: {file_name}", state="running")
                    st.write(f"**[{idx}/{total_files}] Processing {file_name}**")

                    stages = [
                        "📤 Uploading File...",
                        "📄 Extracting Text...",
                        "🧩 Chunking Document...",
                        "🧠 Generating Embeddings...",
                        "🐘 Saving to Database...",
                        "⚡ Indexing in Qdrant...",
                    ]

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(perform_upload, file_name, file_bytes, file_type)

                        stage_idx = 0
                        while not future.done():
                            if stage_idx < len(stages):
                                st.write(stages[stage_idx])
                                stage_idx += 1
                            time.sleep(0.3)

                        try:
                            response = future.result()
                            response.raise_for_status()
                            payload = response.json()

                            while stage_idx < len(stages):
                                st.write(stages[stage_idx])
                                stage_idx += 1
                                time.sleep(0.1)

                            successful_uploads.append(payload["file_name"])
                            st.write(f"✅ Finished: {file_name}")
                        except Exception as exc:
                            st.error(f"Failed {file_name}: {format_error_message(exc)}")

                if successful_uploads:
                    upload_status.update(label=f"✅ Successfully ingested {len(successful_uploads)} document(s)!", state="complete", expanded=False)
                    st.session_state["toast_msg"] = f"Successfully uploaded {len(successful_uploads)} file(s)!"
                    st.session_state["uploader_key"] += 1
                    st.rerun()
                else:
                    upload_status.update(label="❌ Upload Failed", state="error", expanded=True)

    st.markdown("---")
    col_hdr, col_ref = st.columns([3, 1])
    with col_hdr:
        st.subheader("📄 Managed Documents")
    with col_ref:
        if st.button("🔄", help="Refresh Document List"):
            st.rerun()

    documents = fetch_documents()

    if not documents:
        st.caption("No documents uploaded yet.")
    else:
        for doc in documents:
            doc_id = doc["id"]
            file_name = doc["file_name"]
            upload_time_ist = format_local_timestamp(doc["uploaded_at"])
            pages = doc.get("pages", 1)
            chunks = doc.get("chunk_count", 0)
            size_kb = round(doc.get("size_bytes", 0) / 1024, 1)

            with st.container(border=True):
                st.markdown(f"📄 **{file_name}**")
                st.caption(f"📅 {upload_time_ist} | 📦 {size_kb} KB")
                st.caption(f"📑 {pages} Pages | 🧩 {chunks} Chunks")

                # Single document delete button & state-based confirmation box
                if st.session_state.get("confirm_delete_id") == doc_id:
                    st.warning(f"Delete **{file_name}**?")
                    c1, c2 = st.columns(2)
                    if c1.button("Yes", key=f"yes_del_{doc_id}", type="primary", use_container_width=True):
                        try:
                            res = requests.delete(f"{DOCUMENTS_API_URL}/{doc_id}", timeout=10)
                            res.raise_for_status()
                            st.session_state.pop("confirm_delete_id", None)
                            st.session_state["toast_msg"] = f"Deleted {file_name}"
                            st.rerun()
                        except Exception as exc:
                            st.error(format_error_message(exc))
                    if c2.button("Cancel", key=f"cancel_del_{doc_id}", use_container_width=True):
                        st.session_state.pop("confirm_delete_id", None)
                        st.rerun()
                else:
                    if st.button("🗑️ Delete", key=f"del_btn_{doc_id}", use_container_width=True):
                        st.session_state["confirm_delete_id"] = doc_id
                        st.session_state.pop("confirm_delete_all", None)
                        st.rerun()

        st.markdown("---")
        # Bulk delete button & state-based confirmation box
        if st.session_state.get("confirm_delete_all"):
            st.error("Delete ALL documents & vectors?")
            ca1, ca2 = st.columns(2)
            if ca1.button("Yes, Delete All", key="yes_del_all", type="primary", use_container_width=True):
                try:
                    res = requests.delete(DOCUMENTS_API_URL, timeout=10)
                    res.raise_for_status()
                    st.session_state.pop("confirm_delete_all", None)
                    st.session_state["toast_msg"] = "Deleted all documents and vectors."
                    st.rerun()
                except Exception as exc:
                    st.error(format_error_message(exc))
            if ca2.button("Cancel", key="cancel_del_all", use_container_width=True):
                st.session_state.pop("confirm_delete_all", None)
                st.rerun()
        else:
            if st.button("⚠️ Delete All Documents", key="btn_del_all", use_container_width=True):
                st.session_state["confirm_delete_all"] = True
                st.session_state.pop("confirm_delete_id", None)
                st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# --- MAIN VIEW: ChatGPT-Style Chat Interface ---
st.session_state.setdefault("messages", [])

# Empty state welcome screen
if not st.session_state["messages"]:
    st.markdown(
        """
        <div style="text-align: center; padding: 40px 20px;">
            <h2>👋 Welcome to KnowledgeFlow AI</h2>
            <p style="color: #666; font-size: 1.1em;">
                Upload your enterprise documents in the sidebar, then ask questions below to receive grounded answers with exact source citations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_citation_cards(citations: list[dict], results: list[dict]):
    """Render professional expandable citation cards for retrieved sources."""
    if not citations and not results:
        return

    st.markdown("##### 📌 Grounded Source Citations")

    text_map = {}
    if results:
        for hit in results:
            p = hit.get("payload", {})
            fn = p.get("filename", "Unknown")
            cid = p.get("chunk_id", 0)
            txt = p.get("chunk_text", "")
            text_map[(fn, cid)] = txt

    cards_to_render = []
    if citations:
        for cite in citations:
            fn = cite.get("filename", "Unknown")
            cid = cite.get("chunk_id", 0)
            score = cite.get("score", 0.0)
            start_off = cite.get("start_offset", 0)
            end_off = cite.get("end_offset", 0)
            txt = text_map.get((fn, cid), "")
            cards_to_render.append({
                "filename": fn,
                "chunk_id": cid,
                "score": score,
                "start_offset": start_off,
                "end_offset": end_off,
                "text": txt,
            })
    elif results:
        for hit in results:
            p = hit.get("payload", {})
            cards_to_render.append({
                "filename": p.get("filename", "Unknown"),
                "chunk_id": p.get("chunk_id", 0),
                "score": hit.get("score", 0.0),
                "start_offset": p.get("start_offset", 0),
                "end_offset": p.get("end_offset", 0),
                "text": p.get("chunk_text", ""),
            })

    for card in cards_to_render:
        match_pct = f"{card['score'] * 100:.1f}%" if card['score'] <= 1.0 else f"{card['score']:.4f}"
        expander_title = f"📖 **{card['filename']}** (Chunk {card['chunk_id']}) — `{match_pct}` match"
        with st.expander(expander_title, expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.caption(f"📄 **Document**: {card['filename']}")
            with c2:
                st.caption(f"🧩 **Chunk ID**: {card['chunk_id']} | 🎯 **Score**: `{match_pct}`")
            with c3:
                st.caption(f"📍 **Offsets**: {card['start_offset']} - {card['end_offset']}")
            if card["text"]:
                st.markdown("**Chunk Content Preview:**")
                st.info(card["text"])


# Render conversation history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("citations") or msg.get("results"):
            render_citation_cards(msg.get("citations", []), msg.get("results", []))

# Sticky ChatGPT input box with document availability guard
if not documents:
    st.chat_input("Please upload a document in the sidebar to begin asking questions...", disabled=True)
else:
    if prompt := st.chat_input("Ask KnowledgeFlow AI a question about your documents..."):
        # Append & display user message turn immediately
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Render streaming assistant response turn
        with st.chat_message("assistant"):
            citations = []
            results = []

            # Staged status loader
            status_box = st.status("🔍 Searching documents...", expanded=False)

            def token_stream():
                try:
                    status_box.update(label="📑 Preparing retrieved context...", state="running")
                    backend_ask_url = API_URL.replace("/upload", "/ask")
                    history_payload = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state["messages"][:-1]
                        if m.get("role") in ("user", "assistant")
                    ]

                    response = requests.post(
                        backend_ask_url,
                        json={"query": prompt, "limit": 5, "history": history_payload},
                        stream=True,
                        timeout=60,
                    )
                    response.raise_for_status()

                    first_token = True
                    for line in response.iter_lines():
                        if line:
                            decoded = line.decode("utf-8")
                            if decoded.startswith("data: "):
                                decoded = decoded[6:]
                            try:
                                event = json.loads(decoded)
                                if event.get("type") == "metadata":
                                    citations.extend(event.get("citations", []))
                                    results.extend(event.get("results", []))
                                elif event.get("type") == "token":
                                    if first_token:
                                        status_box.update(label="✨ Generating grounded answer...", state="complete")
                                        first_token = False
                                    yield event.get("text", "")
                                elif event.get("type") == "error":
                                    status_box.update(label="❌ Generation issue", state="error")
                                    st.error(event.get("message", "A streaming error occurred."))
                            except Exception:
                                pass
                    if first_token:
                        status_box.update(label="✨ Response complete", state="complete")
                except Exception as exc:
                    status_box.update(label="❌ Request failed", state="error")
                    st.error(format_error_message(exc))

            full_answer = st.write_stream(token_stream())

            if citations or results:
                render_citation_cards(citations, results)

        # Store assistant response in session memory
        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": full_answer,
                "citations": citations,
                "results": results,
            }
        )
        st.rerun()
