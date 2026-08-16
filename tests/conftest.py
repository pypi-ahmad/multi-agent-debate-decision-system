# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_rag_store(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("debate_decision_system.config.RAG_EMBED_BACKEND", "hash")
    monkeypatch.setattr("debate_decision_system.rag.vectorstore.STORE_PATH", tmp_path / "lancedb")
