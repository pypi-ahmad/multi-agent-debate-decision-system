# Copyright (c) 2026 Ahmad Mujtaba
"""Local embeddings: hashed fallback, Ollama nomic/bge when available."""

from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.request
from urllib.parse import urlparse

from debate_decision_system import config
from debate_decision_system.config import OLLAMA_BASE_URL

HASH_DIM = 256


class _EmbedState:
    ollama_dead = False


def _tokens(text: str) -> list[str]:
    return [part.lower() for part in text.replace("/", " ").split() if len(part) > 1]


def _l2(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def hashed_embed(text: str, dim: int = HASH_DIM) -> list[float]:
    """Deterministic bag-of-tokens embedding. No network. Tests and offline."""
    vec = [0.0] * dim
    for token in _tokens(text) or ["_empty"]:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[bucket] += sign
    return _l2(vec)


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


def _ollama_embed(text: str, model: str) -> list[float] | None:
    root = OLLAMA_BASE_URL.rstrip("/")
    parsed = urlparse(root)
    if parsed.scheme not in {"http", "https"}:
        return None
    body = json.dumps({"model": model, "input": text}).encode()
    req = urllib.request.Request(  # noqa: S310
        f"{root}/api/embed",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as response:  # noqa: S310
            payload = json.loads(response.read().decode())
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return _ollama_embed_legacy(text, model, root)
    rows = payload.get("embeddings") or []
    if rows and isinstance(rows[0], list):
        return [float(x) for x in rows[0]]
    return None


def _ollama_embed_legacy(text: str, model: str, root: str) -> list[float] | None:
    body = json.dumps({"model": model, "prompt": text}).encode()
    req = urllib.request.Request(  # noqa: S310
        f"{root}/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as response:  # noqa: S310
            payload = json.loads(response.read().decode())
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
    row = payload.get("embedding")
    if isinstance(row, list) and row:
        return [float(x) for x in row]
    return None


def embed_text(text: str) -> tuple[list[float], str]:
    """Return (vector, backend). Prefer Ollama; fall back to hashed."""
    backend = config.RAG_EMBED_BACKEND.strip().lower()
    model = config.RAG_EMBED_MODEL
    if backend != "hash" and not _EmbedState.ollama_dead:
        vector = _ollama_embed(text, model)
        if vector:
            return vector, "ollama"
        _EmbedState.ollama_dead = True
        if backend == "ollama":
            return hashed_embed(text), "hash"
    return hashed_embed(text), "hash"
