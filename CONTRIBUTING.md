# Contributing

Thank you for wanting to help. This project is free, MIT-licensed, and community-driven. You run it on your own machine with your own keys. Please do not offer money, donations, or sponsorship — none is wanted.

## Ways to help

- Use the app and report what broke
- Open a [bug report](.github/ISSUE_TEMPLATE/bug_report.md)
- Suggest a feature with the [feature request](.github/ISSUE_TEMPLATE/feature_request.md) template
- Send a pull request against `main`

Read [SUPPORT.md](SUPPORT.md) if you only need help using the app. Read [DISCLAIMER.md](DISCLAIMER.md) before you feed it real documents or decisions.

## Local setup

```bash
uv sync --all-groups
copy .env.example .env   # Unix: cp .env.example .env
```

Put **your** keys in `.env` if you are not using Ollama only. Never commit `.env`, `data/decisions.db`, `data/lancedb/`, or debate JSON.

Windows: double-click `run.cmd`. Other systems: `uv run streamlit run app.py` then open http://localhost:8522.

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

## How to send a change

1. Fork the repo and branch from `main` (`phase-…` or `fix-…` is fine).
2. Keep the change small. Match nearby style (`from __future__ import annotations`, Ruff `ALL`).
3. Open a PR using [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).
4. Wait for CI (`quality` + `hooks`) on the PR.

Do not change the provider rules: Ollama lists local tags; OpenAI is only `gpt-5.6-luna` and `gpt-5.6-terra` at medium effort; Agnes is fixed `agnes-2.5-flash`; Google is `gemini-3.5-flash-lite` and `gemini-3.7-flash`. Keys stay in environment variables.

## Security

Do not file a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
