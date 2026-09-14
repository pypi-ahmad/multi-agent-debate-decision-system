# Copyright (c) 2026 Ahmad Mujtaba
"""Advanced RAG: hybrid retrieve, rerank, citations.

Read pipeline.py first — it's the orchestrator that calls embeddings.py,
retriever.py (hybrid search), reranker.py, and vectorstore.py in sequence.
"""

from __future__ import annotations

from debate_decision_system.rag.pipeline import (
    IndexReport,
    RagHit,
    RagResult,
    index_decision,
    index_documents,
    run_rag,
)
from debate_decision_system.rag.vectorstore import delete_source
from debate_decision_system.rag.vectorstore import stats as store_stats

__all__ = [
    "IndexReport",
    "RagHit",
    "RagResult",
    "delete_source",
    "index_decision",
    "index_documents",
    "run_rag",
    "store_stats",
]
