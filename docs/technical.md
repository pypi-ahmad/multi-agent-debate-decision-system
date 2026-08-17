# Technical documentation

How the current system is put together. Recipes: [how-to-use.md](how-to-use.md). Cited map: [ARCHITECTURE.md](../ARCHITECTURE.md).

Repo: https://github.com/pypi-ahmad/multi-agent-debate-decision-system

## What this is

A Python package (`debate-decision-system` `0.3.0`) and a Streamlit app. One LangGraph hearing produces a structured verdict. Persistence is local SQLite plus a LanceDB vector store. There is no auth and no hosted API of our own.

The console entry `debate-decision-system` only prints `debate-decision-system 0.3.0`. The product is Streamlit on port **8522**.

## Layers

| Layer | Location | Job |
| --- | --- | --- |
| Nav | `app.py` | `st.navigation`: Debate, Decision history, Analytics, Knowledge |
| Hearing UI | `app_pages/debate.py` | Seats, step loop, inject, export, RAG toggle |
| History UI | `app_pages/history.py` | Search, continue, link, re-run |
| Analytics UI | `app_pages/analytics.py` | Charts, quality, simulation |
| Knowledge UI | `app_pages/knowledge.py` | Library upload, LanceDB stats, search test |
| Graph | `graph.py` | `initial_state`, `advance`, inject, evidence |
| Nodes | `agents/` | options, pros/cons, moderator, huddle, debater, judge |
| Tools | `tools.py` | calculator, code, wikipedia, web_search, docs, `tool:rag` |
| Teams | `teams.py` | templates, leader, huddle members |
| Memory | `memory.py` | SQLite `data/decisions.db`; `history.py` re-exports |
| RAG | `rag/` | embeddings, LanceDB store, hybrid retrieve, rerank, pipeline |
| Analytics | `analytics.py` | overlap, wins, quality, strength over time, reset, run-until-done |
| Docs load | `documents.py` | text, PDF (`pypdf`), zip |

The UI never talks to providers. It calls `advance`.

## Runtime and providers

`.env` is loaded from the repo root. OS env wins.

| Provider | Models | Env | Client |
| --- | --- | --- | --- |
| Ollama | `GET {base}/api/tags` | none; optional `OLLAMA_BASE_URL` (default `http://localhost:11434`) | `ChatOllama` |
| OpenAI | `gpt-5.6-luna`; effort `medium` | `OPENAI_API_KEY`; optional `OPENAI_BASE_URL` (default `https://api.openai.com/v1`) | `ChatOpenAI` |
| Agnes AI | `agnes-2.5-flash` | `AGNES_API_KEY`; optional `AGNES_BASE_URL` (default `https://apihub.agnes-ai.com/v1`) | `ChatOpenAI` @ `AGNES_BASE_URL` |
| Google | `gemini-3.5-flash-lite`, `gemini-3.7-flash` | `GOOGLE_API_KEY` | `ChatGoogleGenerativeAI` |

`local_only` rewrites every seat and member to Ollama.

> **`gemini-3.7-flash` ignores temperature.** The model does not accept `temperature`, `top_p`, or `top_k`; those parameters are stripped before the request is sent (`config.GOOGLE_NO_SAMPLING`, `llm.py`). The temperature slider has no effect for this model.

Bounds: 2–8 seats, 1–6 rounds, 2–4 team members, temperature 0.0–1.2, speaking order sequential / reverse / random. Ten personas. Timeouts 120s Ollama, 90s hosted.

Defaults: 2 seats, 2 rounds, temperature 0.4, speaking order sequential.

## Graph

Live path (`next_action` / `advance`):

1. Structured: `options` → `pros_cons` (Analyst turns).
2. `moderator` (or `{phase: judge}` when `speeches_done >= rounds * seats`).
3. `tools` — plan up to 2 tool calls; if RAG is on, append a `tool:rag` citation turn.
4. `huddle` — only if the current seat `kind==team` and huddle is not done; one member per step.
5. `debater` — individual persona, or team leader using huddle notes. Public name is the seat name.
6. Repeat until judge.

`awaiting_speech` is set by `tools_node`. `huddle_done` / `huddle_index` reset after a public speech.

Human inject does not increment `speeches_done`. `request_evidence` retargets `next_speaker` to the last public debater.

Compiled `debate_graph` exists in `graph.py` but the UI steps with `advance()`, not `invoke`.

`judge_node` formats the transcript with `limit=24` (the 24 most recent turns are passed to the judge LLM).

## Grounding and tools

| Knowledge | Allowed tools |
| --- | --- |
| `open` | calculator, code, docs, wikipedia, web_search |
| `grounded` | calculator, code, docs |

Code is a restricted `ast` math expression (no import, no attribute access). Allowed names: all `math` module functions plus `abs`, `min`, `max`, `sum`, `round`, `len`. Calculator is numbers and `+ - * / // ** %` (floor division `//` included). Wikipedia is the REST summary API (`/api/rest_v1/page/summary/{title}`). Web search is DuckDuckGo Instant Answer JSON. Docs is keyword overlap plus RAG when enabled.

In grounded mode, if documents exist and the speech has no `[`, the debater is asked once to cite.

## RAG

`knowledge_block` calls `context_for_state` unless `rag_enabled` is false (then keyword `retrieve` only).

Pipeline: rewrite query → dense LanceDB search + BM25 → RRF → feature rerank (`llm_rerank` optional) → sentence compression → `[source: type:name#chunk]`.

Store: `data/lancedb/` (`STORE_PATH`). Incremental upsert by content hash.

Embeddings (`RAG_EMBED_BACKEND`, default `auto`):
- `auto` — tries Ollama with `RAG_EMBED_MODEL` (default `nomic-embed-text`); also tries `bge-small` as a fallback Ollama model; falls back to the hashed backend if no Ollama embed model responds.
- `hash` — always use the deterministic 256-d hashed embedding (no Ollama required; no semantic similarity).

Collections: `session` (this debate’s uploads) vs `longterm` (Knowledge page + indexed decisions). `save_debate` calls `index_decision`. `delete_decision` drops those vectors. Multi-hop follows `decision_links`.

## Personas

Ten built-in personas (`personas.py`). Without an explicit selection, `assign_personas(n)` picks the first `n` in this order:

| # | Name | Style |
| --- | --- | --- |
| 1 | Pragmatist | ships the smallest thing that works |
| 2 | Skeptic | hunts hidden failure modes |
| 3 | First-principles | rebuilds from constraints |
| 4 | Devil's advocate | argues the opposite of the room |
| 5 | Ethicist | tracks stakeholders and second-order harm |
| 6 | Operator | asks who does the work on Monday |
| 7 | Optimistic | looks for upside and reversible bets |
| 8 | Data-driven | demands numbers and base rates |
| 9 | Risk-averse | minimizes downside and tail risk |
| 10 | Creative | offers a third option the room did not name |

`select_personas(names)` resolves a list of names; unknown names are silently skipped. Each seat also accepts a per-seat provider and model override.

## Teams

A seat is `kind=agent` or `kind=team`. Team templates live in `TEAM_TEMPLATES`. Huddle turns use `role=huddle` and `name="{team} / {persona}"`. The leader's public turn is `role=debater` with the team name.

## Memory

`save_debate` upserts `decisions` (topic, timestamps, status, recommendation, confidence, outcome, winner, participants, `agent_models`, arguments, transcript text, tags, category, notes, `archived` flag, full `state_json`). `decision_links` stores undirected pairs. `search_decisions` uses FTS5 plus `LIKE` fallback.

Status values: `in_progress`, `decided`, `archived`. The History UI can filter by all three; `archived` debates are hidden from the default view but are not deleted.

`load_debate` reads SQLite; if missing, it ingests a leftover `data/debates/<id>.json` (legacy JSON files from earlier versions are stored there).

## Analytics

`quality_report` computes participation, Jaccard-style token overlap on consecutive public speeches (flag ≥ 0.55), mean score axes, and a one-paragraph summary. `strength_over_time` averages those means by date. `reset_for_rerun` deep-copies a state, new `debate_id`, empty transcript. `run_until_done` loops `advance` (used by simulation). Win rates come from decided SQLite rows.

## Export

`export.py` provides two functions used by the UI:

- `debate_to_markdown(state)` — full Markdown summary: topic, verdict table, per-speech scores, and full transcript. Available from the Debate page and the History **Export record** button.
- `timeline_mermaid(state)` — Mermaid sequence diagram of speaker order and roles. Rendered inline on the Debate page after a debate finishes.

## Quality gates

`make lint` / `make test` / `make audit`. Coverage fail-under 80%. CI: frozen `uv sync`, Ruff, ty, pytest, pip-audit, prek.

## Not here

No auth, no multi-user server, no unrestricted `exec`, no CLI that runs a debate.
