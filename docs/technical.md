# Technical documentation

How the current system is put together. Recipes: [how-to-use.md](how-to-use.md). Cited map: [ARCHITECTURE.md](../ARCHITECTURE.md).

Repo: https://github.com/pypi-ahmad/multi-agent-debate-decision-system

## What this is

A Python package (`debate-decision-system` `0.2.0`) and a Streamlit app. One LangGraph hearing produces a structured verdict. Persistence is local SQLite plus a LanceDB vector store. There is no auth and no hosted API of our own.

The console entry `debate-decision-system` only prints `debate-decision-system 0.2.0`. The product is Streamlit on port **8522**.

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
| Ollama | `GET {base}/api/tags` | none | `ChatOllama` |
| OpenAI | `gpt-5.6-luna`; effort `medium` | `OPENAI_API_KEY` + optional `OPENAI_BASE_URL` | `ChatOpenAI` |
| Agnes AI | `agnes-2.5-flash` | `AGNES_API_KEY` | `ChatOpenAI` @ `AGNES_BASE_URL` |
| Google | `gemini-3.5-flash-lite`, `gemini-3.7-flash` | `GOOGLE_API_KEY` | `ChatGoogleGenerativeAI` |

`local_only` rewrites every seat and member to Ollama.

Bounds: 2–8 seats, 1–6 rounds, 2–4 team members, temperature 0.0–1.2, speaking order sequential / reverse / random. Ten personas. Timeouts 120s Ollama, 90s hosted.

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

## Grounding and tools

| Knowledge | Allowed tools |
| --- | --- |
| `open` | calculator, code, docs, wikipedia, web_search |
| `grounded` | calculator, code, docs |

Code is a restricted `ast` math expression (no import, no attributes). Calculator is numbers and `+ - * / ** %`. Wikipedia is the REST summary API. Web search is DuckDuckGo Instant Answer JSON. Docs is keyword overlap plus RAG when enabled.

In grounded mode, if documents exist and the speech has no `[`, the debater is asked once to cite.

## RAG

`knowledge_block` calls `context_for_state` unless `rag_enabled` is false (then keyword `retrieve` only).

Pipeline: rewrite query → dense LanceDB search + BM25 → RRF → feature rerank (`llm_rerank` optional) → sentence compression → `[source: type:name#chunk]`.

Store: `data/lancedb/` (`STORE_PATH`). Incremental upsert by content hash. Embeddings: Ollama `RAG_EMBED_MODEL` (default `nomic-embed-text`) or hashed 256-d fallback (`RAG_EMBED_BACKEND=hash`).

Collections: `session` (this debate’s uploads) vs `longterm` (Knowledge page + indexed decisions). `save_debate` calls `index_decision`. `delete_decision` drops those vectors. Multi-hop follows `decision_links`.

## Teams

A seat is `kind=agent` or `kind=team`. Team templates live in `TEAM_TEMPLATES`. Huddle turns use `role=huddle` and `name="{team} / {persona}"`. The leader's public turn is `role=debater` with the team name.

## Memory

`save_debate` upserts `decisions` (topic, timestamps, status, recommendation, confidence, outcome, winner, participants, `agent_models`, arguments, transcript text, tags, category, notes, full `state_json`). `decision_links` stores undirected pairs. `search_decisions` uses FTS5 plus `LIKE` fallback.

`load_debate` reads SQLite; if missing, it will ingest a leftover `data/debates/<id>.json`.

## Analytics

`quality_report` computes participation, Jaccard-style token overlap on consecutive public speeches (flag ≥ 0.55), mean score axes, and a one-paragraph summary. `strength_over_time` averages those means by date. `reset_for_rerun` deep-copies a state, new `debate_id`, empty transcript. `run_until_done` loops `advance` (used by simulation). Win rates come from decided SQLite rows.

## Quality gates

`make lint` / `make test` / `make audit`. Coverage fail-under 80%. CI: frozen `uv sync`, Ruff, ty, pytest, pip-audit, prek.

## Not here

No auth, no multi-user server, no unrestricted `exec`, no CLI that runs a debate.
