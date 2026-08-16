# Copyright (c) 2026 Ahmad Mujtaba
from __future__ import annotations

from debate_decision_system import __version__, main, version_banner


def test_version_is_semver() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_version_banner_includes_name_and_version() -> None:
    banner = version_banner()
    assert banner.startswith("debate-decision-system ")
    assert __version__ in banner


def test_main_prints_banner(capsys) -> None:
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == version_banner()
    assert captured.err == ""
