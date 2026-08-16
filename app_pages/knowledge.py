# Copyright (c) 2026 Ahmad Mujtaba
"""Long-term knowledge: uploads, vector status, search test."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from debate_decision_system.config import PROJECT_ROOT, RAG_EMBED_BACKEND, RAG_EMBED_MODEL
from debate_decision_system.documents import load_upload
from debate_decision_system.rag.pipeline import index_documents, run_rag
from debate_decision_system.rag.vectorstore import all_chunks, delete_source, stats

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"


def _save_uploads(files: list[object]) -> list[dict[str, str]]:
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    docs: list[dict[str, str]] = []
    for uploaded in files:
        name = str(getattr(uploaded, "name", "upload"))
        data = bytes(uploaded.read())  # type: ignore[union-attr]
        (KNOWLEDGE_DIR / Path(name).name).write_bytes(data)
        docs.extend(load_upload(name, data))
    return docs


st.title("Knowledge")
st.caption("Long-term library for RAG. Debate uploads stay short-term unless you add them here.")

info = stats()
c1, c2, c3 = st.columns(3)
c1.metric("Chunks", info["chunks"])
c2.metric("Sources", info["sources"])
c3.metric("Last updated", info["last_updated"] or "never")
st.caption(f"LanceDB `{info['path']}` · embed `{RAG_EMBED_BACKEND}` · model `{RAG_EMBED_MODEL}`")
if info["by_type"]:
    st.caption("By type: " + ", ".join(f"{key}={value}" for key, value in info["by_type"].items()))

uploads = st.file_uploader(
    "Add to the library",
    type=["txt", "md", "csv", "json", "py", "pdf", "zip", "toml", "yml", "yaml"],
    accept_multiple_files=True,
)
if uploads and st.button("Index uploads", icon=":material/upload_file:"):
    docs = _save_uploads(list(uploads))
    report = index_documents(docs, collection="longterm")
    st.toast(f"Indexed {report.upserted} chunks from {report.sources} files")
    st.rerun()

st.subheader("Search test")
query = st.text_input("Query", placeholder="Why did we choose SQLite?")
source_type = st.segmented_control(
    "Source type",
    ["any", "document", "decision"],
    default="any",
    key="rag_type",
)
if query and st.button("Search", icon=":material/search:"):
    types = None if source_type == "any" else (source_type,)
    result = run_rag(query, documents=[], source_types=types, hops=1)
    if not result.hits:
        st.caption("No hits.")
    for hit in result.hits:
        with st.container(border=True):
            st.markdown(f"**{hit.citation}** · score {hit.score:.3f} · {hit.collection}")
            st.markdown(hit.text)

st.subheader("Sources")
seen: set[tuple[str, str]] = set()
for chunk in all_chunks():
    key = (chunk.source_type, chunk.source_id)
    if key in seen:
        continue
    seen.add(key)
    left, right = st.columns((4, 1), vertical_alignment="center")
    left.markdown(f"`{chunk.source_type}` · **{chunk.source_name}**")
    if right.button("Remove", key=f"rm_{chunk.source_type}_{chunk.source_id}"):
        delete_source(chunk.source_type, chunk.source_id)
        st.rerun()
