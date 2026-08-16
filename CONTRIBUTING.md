# Contributing

Thank you for showing up. This project is **free**, MIT-licensed, and community-driven. You are welcome here whether you file a typo, a failing test, or a careful feature.

You run the app on **your** machine with **your** keys. Please do **not** offer money, donations, or sponsorship — none is wanted. Time and clear reports are enough.

Before you feed the app real documents or decisions, read [DISCLAIMER.md](DISCLAIMER.md). You are fully responsible for that data.

## Ways to help

- Clone the repo and actually run a debate (`run.cmd` or `./run.sh`)
- Open a [bug report](.github/ISSUE_TEMPLATE/bug_report.md) when something does not match the docs
- Suggest a feature with the [feature request](.github/ISSUE_TEMPLATE/feature_request.md) template
- Send a pull request against `main`
- Improve docs when you trip over something

Usage questions belong in [SUPPORT.md](SUPPORT.md) first. Vulnerabilities belong in [SECURITY.md](SECURITY.md), not a public issue.

## Ground rules

- Be kind. First-time contributors get the same patience as regulars.
- Keep changes small and scoped.
- Do not add donation buttons, sponsor files, or payment links.
- Do not add a hosted multi-user service or authentication unless that is an agreed design.
- Do not add unrestricted `exec` / `eval` / shell tools.
- Provider catalogs stay locked unless the issue is about them: Ollama lists local tags; OpenAI is `gpt-5.6-luna` at medium effort; Agnes is `agnes-2.5-flash`; Google is `gemini-3.5-flash-lite` and `gemini-3.7-flash`. Keys stay in environment variables. OS env wins over `.env`.

## Local setup

```bash
git clone https://github.com/pypi-ahmad/multi-agent-debate-decision-system.git
cd multi-agent-debate-decision-system
uv sync --all-groups
```

Copy the env template if you will use hosted models:

```bash
# Windows cmd
copy .env.example .env

# Linux
cp .env.example .env
```

Put **your** keys in `.env` or in your OS environment. Never commit `.env`, `data/decisions.db`, `data/lancedb/`, or debate JSON.

Launch:

- Windows (native, not WSL): double-click `run.cmd`
- Linux: `./run.sh`

Open http://localhost:8522. Both launchers create a repo-root `.venv` with uv and run Streamlit inside it.

## Checks before a PR

```bash
make lint
make test
```

Or:

```bash
uv run ruff format --check
uv run ruff check
uv run ty check src/
uv run pytest
```

Coverage must stay at or above 80%. Tests use fake chat clients. Do not add a live-LLM end-to-end suite.

Add runtime dependencies with `uv add <package>`. Do not edit the dependency lists in `pyproject.toml` by hand.

Match nearby style: `from __future__ import annotations`, Ruff `ALL`.

## How to send a change

1. Fork the repo and branch from `main` (`fix-…` or `feat-…` is fine).
2. Prefer an issue first if the change is large.
3. Open a PR using [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).
4. Wait for CI (`quality` + `hooks`) on the PR.

## Security

Do not file a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
