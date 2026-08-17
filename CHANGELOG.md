# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.1] — 2026-08-17

### Added

- **CHANGELOG.md** — this file
- **CONTRIBUTING.md** — rewritten: ways-to-contribute table (10 rows), local setup, quality checks, PR workflow, explicit no-financial-support statement
- **`.github/ISSUE_TEMPLATE/bug_report.md`** — environment table, terminal output paste block, warmer tone, DISCLAIMER note
- **`.github/ISSUE_TEMPLATE/feature_request.md`** — scoped feature-request template with "Does it belong here?" checklist
- **`.github/PULL_REQUEST_TEMPLATE.md`** — type checklist, quality-gate checklist, no-donation rule, DISCLAIMER note

### Changed

- **`docs/technical.md`** — full rewrite from source: 27-module map, all 23 `DebateState` fields with types and reducer annotations, all nested types, provider table with env defaults and timeouts, `GOOGLE_NO_SAMPLING` warning, graph wiring and `next_action` rule chain, all 7 agents with inputs/outputs, all 5 tools with modes, 10 personas with instructions, 5 team templates, RAG pipeline (chunking params, 5-step pipeline, collections, embed backends), SQLite schema (all columns + FTS5 table), all memory functions, all analytics functions, export functions, full configuration constant table
- **`docs/how-to-use.md`** — full rewrite: 15 step-by-step recipes covering first launch, zero-key Ollama run, hosted models, structured mode, persona selection, team seats, grounded mode, RAG library, pause/inject, evidence requests, continuing past debates, search/tag/archive, export, and analytics simulation
- **`README.md`** — comprehensive rewrite: expanded intro paragraph, full features section (engine, seats/personas, tools/grounding, decision report, memory, analytics), providers table with base-URL defaults, common-tasks quick-reference table, architecture Mermaid diagram, 9-row documentation reference table, contributing section, development section, "Made with ❤️ by Ahmad Mujtaba" footer
- **`docs/how-to-use.md`** (earlier) — added `Optional env` column to providers table, added Personas section (10-persona table), expanded search/archive/export recipes, `gemini-3.7-flash` temperature note
- **`docs/technical.md`** (earlier) — added OLLAMA_BASE_URL and AGNES_BASE_URL defaults, `gemini-3.7-flash` temperature-stripping warning, defaults line, judge transcript limit, `//` operator in calculator, math functions in code tool, RAG embed backend details, archived status, legacy debates dir, Personas and Export sections

### Infrastructure

- Windows `run.cmd` updated to create a project-root `.venv` via uv
- Linux `run.sh` added as a native launcher (same venv strategy)
- Architecture maps and interactive knowledge graphs added (`ARCHITECTURE.md`, `Project_Architecture_Blueprint.md`)

---

## [0.3.0] — 2026-07-01

Initial public release.

- LangGraph debate graph: options → pros/cons → hearing → judgment
- 7 nodes: options, pros_cons, moderator, tools, huddle, debater, judge
- 5 tools: calculator, code, wikipedia, web_search, docs
- 10 personas, 5 team templates
- LanceDB hybrid RAG (dense + BM25, rerank, citations)
- SQLite decision memory with FTS5 search
- Streamlit UI: Debate, Decision history, Analytics, Knowledge pages
- Markdown export and Mermaid timeline
- Native Windows (`run.cmd`) and Linux (`run.sh`) launchers
- CI: Ruff, ty, pytest (coverage ≥ 80%), pip-audit, pre-commit

---

## [0.2.0]

Internal pre-release.

[0.3.1]: https://github.com/pypi-ahmad/multi-agent-debate-decision-system/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/pypi-ahmad/multi-agent-debate-decision-system/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/pypi-ahmad/multi-agent-debate-decision-system/releases/tag/v0.2.0
