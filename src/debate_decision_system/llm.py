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
    """Flatten a chat result to plain text.

    `.content` shape varies by provider/langchain version: a plain string, or a
    list of content blocks (e.g. reasoning + text parts). Normalize here so
    every caller can treat a chat response as a single string.
    """
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


def _require_key(value: str, name: str) -> str:
    if not value:
        missing = f"{name} is not set. See .env.example."
        raise RuntimeError(missing)
    return value


def _openai_chat(model: str, temperature: float) -> BaseChatModel:
    if model not in config.OPENAI_MODELS:
        msg = f"OpenAI model must be one of {config.OPENAI_MODELS}, got {model!r}"
        raise ValueError(msg)
    return ChatOpenAI(
        model=model,
        api_key=_require_key(config.openai_api_key(), "OPENAI_API_KEY"),
        base_url=config.openai_base_url(),
        temperature=temperature,
        timeout=config.REASONING_TIMEOUT_SECONDS,
        reasoning={"effort": config.OPENAI_REASONING_EFFORT},
    )


def _agnes_chat(temperature: float) -> BaseChatModel:
    return ChatOpenAI(
        model=config.AGNES_MODEL,
        api_key=_require_key(config.agnes_api_key(), "AGNES_API_KEY"),
        base_url=config.agnes_base_url(),
        temperature=temperature,
        timeout=config.REASONING_TIMEOUT_SECONDS,
    )


def _google_chat(model: str, temperature: float) -> BaseChatModel:
    if model not in config.GOOGLE_MODELS:
        msg = f"Google model must be one of {config.GOOGLE_MODELS}, got {model!r}"
        raise ValueError(msg)
    kwargs: dict[str, Any] = {
        "model": model,
        "google_api_key": _require_key(config.google_api_key(), "GOOGLE_API_KEY"),
        "timeout": config.REASONING_TIMEOUT_SECONDS,
    }
    # Some Gemini models (config.GOOGLE_NO_SAMPLING) reject sampling params outright,
    # so temperature is only attached when the model is known to accept it.
    if model not in config.GOOGLE_NO_SAMPLING:
        kwargs["temperature"] = temperature
    return ChatGoogleGenerativeAI(**kwargs)


def get_chat_model(provider: str, model: str, temperature: float = 0.4) -> BaseChatModel:
    """Build the chat client for one debate run."""
    if provider == "Ollama":
        return ChatOllama(
            model=model,
            base_url=config.ollama_base_url(),
            temperature=temperature,
            client_kwargs={"timeout": config.OLLAMA_TIMEOUT_SECONDS},
        )
    if provider == "OpenAI":
        return _openai_chat(model, temperature)
    if provider == "Agnes AI":
        return _agnes_chat(temperature)
    if provider == "Google":
        return _google_chat(model, temperature)
    msg = f"Unknown provider: {provider}"
    raise ValueError(msg)


def format_transcript(turns: Sequence[Mapping[str, Any]], limit: int = 8) -> str:
    """Render the last `limit` turns for a prompt."""
    if not turns:
        return "(no speeches yet)"
    recent = turns[-limit:]
    return "\n\n".join(f"{turn['name']} ({turn['role']}): {turn['content']}" for turn in recent)
