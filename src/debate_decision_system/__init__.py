# Copyright (c) 2026 Ahmad Mujtaba
"""Multi-Agent Debate Decision System."""

from __future__ import annotations

__all__ = ["__version__", "main", "version_banner"]
__version__ = "0.2.0"


def version_banner() -> str:
    """Return the CLI identity string."""
    return f"debate-decision-system {__version__}"


def main() -> None:
    """Print the package identity and exit."""
    print(version_banner())  # noqa: T201
