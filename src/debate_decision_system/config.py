# Copyright (c) 2026 Ahmad Mujtaba
"""Environment-driven configuration for Phase 1 debate."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# OS / user env wins. .env fills only missing keys (for other machines).
load_dotenv(PROJECT_ROOT / ".env", override=False)

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

# Official slugs: OpenAI latest-model.md, Agnes Flash docs, Gemini models list.
OPENAI_MODELS = ("gpt-5.6-luna",)
OPENAI_REASONING_EFFORT = "medium"
AGNES_MODEL = "agnes-2.5-flash"
GOOGLE_MODELS = ("gemini-3.5-flash-lite", "gemini-3.7-flash")
# Gemini 3.7 Flash migration: strip temperature / top_p / top_k.
GOOGLE_NO_SAMPLING = frozenset({"gemini-3.7-flash"})


def env(name: str, default: str = "") -> str:
    """Read a live process env var. Empty string if unset."""
    return os.environ.get(name, default).strip()


def openai_api_key() -> str:
    return env("OPENAI_API_KEY")


def openai_base_url() -> str:
    return env("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL) or DEFAULT_OPENAI_BASE_URL


def agnes_api_key() -> str:
    return env("AGNES_API_KEY")


def agnes_base_url() -> str:
    return env("AGNES_BASE_URL", DEFAULT_AGNES_BASE_URL) or DEFAULT_AGNES_BASE_URL


def google_api_key() -> str:
    return env("GOOGLE_API_KEY")


def ollama_base_url() -> str:
    return env("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL) or DEFAULT_OLLAMA_BASE_URL


# Names kept so getattr(config, "OPENAI_API_KEY") still works if something
# imported the old snapshot. Prefer the functions above at call time.
OPENAI_API_KEY = openai_api_key()
OPENAI_BASE_URL = openai_base_url()
AGNES_API_KEY = agnes_api_key()
AGNES_BASE_URL = agnes_base_url()
GOOGLE_API_KEY = google_api_key()
OLLAMA_BASE_URL = ollama_base_url()

RAG_EMBED_MODEL = env("RAG_EMBED_MODEL", "nomic-embed-text") or "nomic-embed-text"
RAG_EMBED_BACKEND = env("RAG_EMBED_BACKEND", "auto") or "auto"

PROVIDERS = ("Ollama", "OpenAI", "Agnes AI", "Google")

MIN_DEBATERS = 2
MAX_DEBATERS = 8
DEFAULT_DEBATERS = 2
MIN_ROUNDS = 1
MAX_ROUNDS = 6
DEFAULT_ROUNDS = 2
DEFAULT_TEMPERATURE = 0.4
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 1.2
SPEAKING_ORDERS = ("sequential", "reverse", "random")
DEFAULT_SPEAKING_ORDER = "sequential"
MIN_TEAM_MEMBERS = 2
MAX_TEAM_MEMBERS = 4

REASONING_TIMEOUT_SECONDS = 90
OLLAMA_TIMEOUT_SECONDS = 120


def models_for_provider(provider: str) -> tuple[str, ...]:
    """Return the fixed model list for a non-Ollama provider."""
    if provider == "OpenAI":
        return OPENAI_MODELS
    if provider == "Agnes AI":
        return (AGNES_MODEL,)
    if provider == "Google":
        return GOOGLE_MODELS
    return ()


def required_key(provider: str) -> str | None:
    """Return the env var name that must be set, or None for Ollama."""
    if provider == "OpenAI":
        return "OPENAI_API_KEY"
    if provider == "Agnes AI":
        return "AGNES_API_KEY"
    if provider == "Google":
        return "GOOGLE_API_KEY"
    return None


def key_present(provider: str) -> bool:
    """True when the provider needs no key or the live env var is set."""
    name = required_key(provider)
    return name is None or bool(env(name))


def list_ollama_models(base_url: str | None = None) -> list[str]:
    """Ask the local Ollama daemon which models are pulled. GET /api/tags."""
    root = (base_url or ollama_base_url()).rstrip("/")
    parsed = urlparse(root)
    if parsed.scheme not in {"http", "https"}:
        return []
    url = f"{root}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310
            payload = json.loads(response.read().decode())
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return []
    names: list[str] = []
    seen: set[str] = set()
    for item in payload.get("models", []):
        name = item.get("name") or item.get("model")
        if isinstance(name, str) and name and name not in seen:
            seen.add(name)
            names.append(name)
    names.sort()
    return names
