# Copyright (c) 2026 Ahmad Mujtaba
"""Turn uploaded bytes (text, PDF, zip, code) into Document records."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from debate_decision_system.state import Document

_TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".py", ".toml", ".yml", ".yaml", ".rst"}
_MAX_CHARS = 20_000


def load_upload(name: str, data: bytes) -> list[Document]:
    suffix = Path(name).suffix.lower()
    if suffix == ".zip":
        return _from_zip(data)
    if suffix == ".pdf":
        return [{"name": name, "text": _pdf_text(data)[:_MAX_CHARS]}]
    text = data.decode("utf-8", errors="replace")[:_MAX_CHARS]
    return [{"name": name, "text": text}]


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader  # noqa: PLC0415

    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages)


def _from_zip(data: bytes) -> list[Document]:
    docs: list[Document] = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            if info.is_dir() or len(docs) >= 20:  # noqa: PLR2004
                continue
            suffix = Path(info.filename).suffix.lower()
            if suffix not in _TEXT_SUFFIXES and suffix != ".pdf":
                continue
            raw = archive.read(info)
            if suffix == ".pdf":
                docs.append({"name": info.filename, "text": _pdf_text(raw)[:_MAX_CHARS]})
            else:
                docs.append(
                    {
                        "name": info.filename,
                        "text": raw.decode("utf-8", errors="replace")[:_MAX_CHARS],
                    }
                )
    return docs
