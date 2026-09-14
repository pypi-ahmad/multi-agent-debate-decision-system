# Contributing

Thank you for showing up. This project is **free**, MIT-licensed, and community-driven. You are welcome here whether you fix a typo, a failing test, or add a carefully scoped feature.

You run the app on **your** machine with **your** keys. Please do **not** offer money, donations, or sponsorship: none of it is needed or wanted. Time and clear reports are more than enough.

Before you feed the app real documents or decisions, read [DISCLAIMER.md](DISCLAIMER.md). You are fully responsible for any data you use.

## Ways to contribute

| Type | How |
| --- | --- |
| Run it | Clone, launch, and actually run a debate: real usage surfaces bugs faster than tests do |
| Bug report | Open a [bug report](.github/ISSUE_TEMPLATE/bug_report.md) when something does not match the docs |
| Feature idea | Use the [feature request](.github/ISSUE_TEMPLATE/feature_request.md) template |
| Persona | Add a new debater persona to `personas.py` with a name, style, and instructions |
| Docs fix | Correct or improve `docs/how-to-use.md`, `docs/technical.md`, or any other doc |
| Tests | Add test coverage in `tests/`; the suite uses fake chat clients (no live LLM calls) |
| RAG | Improve embedding, retrieval, reranking, or citation quality in `rag/` |
| Analytics | Improve win-rate tracking, circular-speech detection, or quality scoring in `analytics.py` |
| Code | Fix a bug or add a scoped feature; open an issue first for large changes |
| Security | Report privately: see [SECURITY.md](SECURITY.md), not a public issue |

Usage questions belong in [SUPPORT.md](SUPPORT.md) first.

## Ground rules

- Be kind. First-time contributors get the same patience as regulars.
- Keep changes small and scoped. Open an issue first for anything large.
- Do not add donation buttons, sponsor files, or payment links.
- Do not add a hosted multi-user service or user authentication.
- Do not add unrestricted `exec` / `eval` / shell tools.
- Provider catalogs stay locked unless the issue is specifically about them: Ollama lists local tags; OpenAI is `gpt-5.6-luna` at medium effort; Agnes is `agnes-2.5-flash`; Google is `gemini-3.5-flash-lite` and `gemini-3.7-flash`. Keys stay in environment variables only. OS env wins over `.env`.

## Local setup

```bash
git clone https://github.com/pypi-ahmad/multi-agent-debate-decision-system.git
cd multi-agent-debate-decision-system
uv sync --all-groups
```

Copy the env template if you plan to use hosted models:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Put **your** keys in `.env` or your OS environment. Never commit `.env`, `data/decisions.db`, `data/lancedb/`, or debate JSON files; they are already in `.gitignore`.

Launch:

| OS | Command |
| --- | --- |
| Windows (native cmd/Explorer, not WSL) | Double-click `run.cmd` |
| Linux | `./run.sh` |

Both launchers install uv if it is missing, create a repo-root `.venv`, sync the lockfile, and start Streamlit from inside the venv. Open <http://localhost:8522>.

## Checks before a PR

```bash
make lint
make test
```

Or run each step individually:

```bash
uv run ruff format --check
uv run ruff check
uv run ty check src/
uv run pytest
```

Coverage must stay at or above **80%**. Tests use fake chat clients; do not add a live-LLM end-to-end suite.

Add runtime dependencies with `uv add <package>`. Do not edit the dependency lists in `pyproject.toml` by hand.

Match the surrounding style: `from __future__ import annotations` at the top of every file, Ruff `ALL` rules.

## How to send a change

1. Fork the repo and create a branch from `main` (e.g. `fix-rag-citation` or `feat-new-persona`).
2. For large changes, open an issue first so we can agree on the approach.
3. Open a PR using the [pull request template](.github/PULL_REQUEST_TEMPLATE.md).
4. CI runs `quality` (Ruff + ty + pytest) and `hooks` (pre-commit) automatically on every PR.
5. A maintainer will review. Please be patient, since this is a volunteer project.

## Security

Do not file a public issue for a vulnerability. Use the private advisory channel described in [SECURITY.md](SECURITY.md).
