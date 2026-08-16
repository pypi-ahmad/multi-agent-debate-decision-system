# Copyright (c) 2026 Ahmad Mujtaba
"""Chat model factory for Ollama, OpenAI, Agnes, and Google."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from debate_decision_system import config


def message_text(message: BaseMessage) -> str:
    """Flatten a chat result to plain text."""
    text = getattr(message, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
                parts.append(str(block.get("text", "")))
        return "".join(parts).strip()
    return str(content).strip()


def get_chat_model(provider: str, model: str, temperature: float = 0.4) -> BaseChatModel:
    """Build the chat client for one debate run."""
    if provider == "Ollama":
        return ChatOllama(
            model=model,
            base_url=config.OLLAMA_BASE_URL,
            temperature=temperature,
            client_kwargs={"timeout": config.OLLAMA_TIMEOUT_SECONDS},
        )

    if provider == "OpenAI":
        if model not in config.OPENAI_MODELS:
            msg = f"OpenAI model must be one of {config.OPENAI_MODELS}, got {model!r}"
            raise ValueError(msg)
        if not config.OPENAI_API_KEY:
            missing = "OPENAI_API_KEY is not set. See .env.example."
            raise RuntimeError(missing)
        return ChatOpenAI(
            model=model,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            temperature=temperature,
            timeout=config.REASONING_TIMEOUT_SECONDS,
            reasoning={"effort": config.OPENAI_REASONING_EFFORT},
        )

    if provider == "Agnes AI":
        if not config.AGNES_API_KEY:
            missing = "AGNES_API_KEY is not set. See .env.example."
            raise RuntimeError(missing)
        return ChatOpenAI(
            model=config.AGNES_MODEL,
            api_key=config.AGNES_API_KEY,
            base_url=config.AGNES_BASE_URL,
            temperature=temperature,
            timeout=config.REASONING_TIMEOUT_SECONDS,
        )

    if provider == "Google":
        if model not in config.GOOGLE_MODELS:
            msg = f"Google model must be one of {config.GOOGLE_MODELS}, got {model!r}"
            raise ValueError(msg)
        if not config.GOOGLE_API_KEY:
            missing = "GOOGLE_API_KEY is not set. See .env.example."
            raise RuntimeError(missing)
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=temperature,
            timeout=config.REASONING_TIMEOUT_SECONDS,
        )

    msg = f"Unknown provider: {provider}"
    raise ValueError(msg)


def format_transcript(turns: Sequence[Mapping[str, Any]], limit: int = 8) -> str:
    """Render the last `limit` turns for a prompt."""
    if not turns:
        return "(no speeches yet)"
    recent = turns[-limit:]
    return "\n\n".join(f"{turn['name']} ({turn['role']}): {turn['content']}" for turn in recent)
