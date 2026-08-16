# Support

This project is free and community-driven. You run it yourself. There is no paid support line and **no donations or sponsorship** — please do not offer money.

## Help yourself first

1. [README.md](README.md) — what the app is and how to start
2. [docs/how-to-use.md](docs/how-to-use.md) — recipes (Ollama, hosted keys, teams, grounding, history)
3. [docs/technical.md](docs/technical.md) — how the graph, tools, RAG, and SQLite memory work
4. [DISCLAIMER.md](DISCLAIMER.md) — your data and your keys

## Common stuck points

| Symptom | Check |
| --- | --- |
| Empty Ollama model list | Is the daemon up? Default `OLLAMA_BASE_URL` is `http://localhost:11434`. |
| “API key is not set” | Copy `.env.example` to `.env` and fill **your** key. OS env wins over the file. |
| `uv sync` failed | Read the error above the prompt. `run.cmd` / `./run.sh` stop if first-time install fails. |
| App not on 8522 | Confirm you used `run.cmd` (Windows) or `./run.sh` (Linux). Port is in `.streamlit/config.toml`. |
| No history rows | Run a debate first. Decisions live in local `data/decisions.db`. |

## Ask the community

- Usage questions and “how do I…?” → a GitHub Discussion if enabled, otherwise an issue labeled as a question
- Bugs → [bug report](.github/ISSUE_TEMPLATE/bug_report.md)
- Ideas → [feature request](.github/ISSUE_TEMPLATE/feature_request.md)
- Security → [SECURITY.md](SECURITY.md) (private advisory, not a public issue)

The maintainer is a volunteer. Be kind. Include OS, Python version, and the command you ran.
