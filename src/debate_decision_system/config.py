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
load_dotenv(PROJECT_ROOT / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODELS = ("gpt-5.6-luna", "gpt-5.6-terra")
OPENAI_REASONING_EFFORT = "medium"

AGNES_API_KEY = os.environ.get("AGNES_API_KEY", "")
AGNES_BASE_URL = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
AGNES_MODEL = "agnes-2.5-flash"

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_MODELS = ("gemini-3.5-flash-lite", "gemini-3.7-flash")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

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


def list_ollama_models(base_url: str | None = None) -> list[str]:
    """Ask the local Ollama daemon which models are pulled."""
    root = (base_url or OLLAMA_BASE_URL).rstrip("/")
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
    for item in payload.get("models", []):
        name = item.get("name") or item.get("model")
        if isinstance(name, str) and name:
            names.append(name)
    return names
