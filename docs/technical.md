# Technical documentation

How the Phase 3 system is put together. For recipes, see [how-to-use.md](how-to-use.md).

Repo: https://github.com/pypi-ahmad/multi-agent-debate-decision-system

## What this is

A Python package (`debate-decision-system`) plus a Streamlit runner (`app.py`). One in-memory LangGraph hearing produces a structured verdict. There is no database, no auth, and no hosted API of our own.

The console entry point `debate-decision-system` only prints `debate-decision-system 0.1.0`. The product surface is Streamlit on port **8522** (`.streamlit/config.toml`).

## Layers

| Layer | Location | Job |
| --- | --- | --- |
| UI | `app.py` | Widgets, step loop, history, upload, export |
| Graph | `src/debate_decision_system/graph.py` | `initial_state`, `advance`, `inject_human`, `request_evidence` |
| Nodes | `src/debate_decision_system/agents/` | options, pros/cons, moderator, debater, judge |
| Models | `src/debate_decision_system/llm.py` | Provider factory |
| Config | `src/debate_decision_system/config.py` | Env keys, catalogs, bounds |
| State | `src/debate_decision_system/state.py` | `DebateState`, `Turn`, `Verdict` |
| Retrieve | `src/debate_decision_system/retrieve.py` | Keyword search over uploads |
| History | `src/debate_decision_system/history.py` | JSON under `data/debates/` |
| Export | `src/debate_decision_system/export.py` | Markdown + mermaid timeline |

`app.py` does not call providers itself. It builds state and calls `advance`.

## Runtime and providers

Keys load from the repo-root `.env` via `python-dotenv` (`config.py`). Variables already set in the OS are not overwritten.

| Provider | How models are chosen | Required env | Client |
| --- | --- | --- | --- |
| Ollama | `GET {OLLAMA_BASE_URL}/api/tags` | none | `ChatOllama` |
| OpenAI | fixed `gpt-5.6-luna`, `gpt-5.6-terra`; reasoning effort `medium` | `OPENAI_API_KEY` | `ChatOpenAI` |
| Agnes AI | fixed `agnes-2.5-flash` | `AGNES_API_KEY` | `ChatOpenAI` against `AGNES_BASE_URL` |
| Google | fixed `gemini-3.5-flash-lite`, `gemini-3.7-flash` | `GOOGLE_API_KEY` | `ChatGoogleGenerativeAI` |

Defaults: OpenAI base `https://api.openai.com/v1`, Agnes base `https://apihub.agnes-ai.com/v1`, Ollama `http://localhost:11434`.

`local_only=True` rewrites the default provider and every seat to Ollama in `initial_state`.

Bounds: 2–8 debaters, 1–6 rounds, temperature 0.0–1.2, speaking order `sequential` | `reverse` | `random`. Ten personas in `personas.py`. `assign_personas(n)` takes the first *n*; the UI uses `select_personas` per seat.

Timeouts: 120s Ollama, 90s hosted.

## State

`DebateState` is a `TypedDict`. Load-bearing fields:

- Identity: `debate_id`, `topic`, `mode` (`open` | `structured`)
- Seats: `debaters[]` each with `name`, `style`, `instructions`, `provider`, `model`; plus `moderator_*` and `judge_*`
- Controls: `max_rounds`, `temperature`, `speaking_order`, `local_only`
- Flow: `phase` (`options` | `pros_cons` | `debate` | `judge`), `next_speaker`, `speeches_done`
- Structured extras: `options`, `pros_cons`
- Knowledge: `documents` (`name`, `text`)
- Accumulators: `transcript` and `errors` (list-append)
- Result: `verdict` (`winner`, `recommendation`, `rationale`, `scores`, `outcome`, `confidence`, `strongest_arguments`, `key_risks`)

A turn `role` is `moderator` | `debater` | `judge` | `human`. Structured Analyst turns use `role=moderator` and `name=Analyst`.

## Control flow

The compiled `debate_graph` is:

`START` → (`options` → `pros_cons` if structured) → `moderator` ⇄ `debater` → `judge` → `END`.

The UI does **not** stream that compiled graph in one shot. It stores `DebateState` in `st.session_state` and calls `advance` once per step (or in a rerun loop when auto-run is on). That is what makes Pause, Inject, and Ask for evidence possible.

`next_action` chooses the node:

1. Stop if `debate_done` (verdict present, or last turn is the judge).
2. `options` / `pros_cons` / `judge` if `phase` says so.
3. `moderator` if there are no turns, the last role is `debater` or `human`, or `speeches_done >= max_rounds * len(debaters)`.
4. `debater` if the last turn is a real moderator (not Analyst). After Analyst, the next action is another moderator so the hearing still opens.

`apply_update` merges node dicts. `transcript` and `errors` concatenate; other keys replace.

`request_evidence` does not call an LLM. It appends a moderator evidence request and sets `next_speaker` to the last debater.

Speaking order (`moderator.next_speaker_index`):

- `sequential`: `speeches_done % n`
- `reverse`: last seat first, then backward
- `random`: `hash((topic, speeches_done, names)) % n` (stable for a process, not across Python hash seeds)

Human inject does not increment `speeches_done`.

## Nodes

Each node returns a partial state update. LLM failures are caught and become a transcript line plus an `errors` entry. The hearing continues.

| Node | File | Model seat | Output |
| --- | --- | --- | --- |
| `options_node` | `agents/structure.py` | moderator | 2–4 options; `phase=pros_cons` |
| `pros_cons_node` | `agents/structure.py` | moderator | `pros_cons` text; `phase=debate` |
| `moderator_node` | `agents/moderator.py` | moderator | floor-giving turn, or `{phase: judge}` when the quota is hit |
| `debater_node` | `agents/debater.py` | that seat | one speech; `speeches_done += 1` |
| `judge_node` | `agents/judge.py` | judge | structured `JudgeOutput` → `verdict` |

The judge asks for `outcome` in `{clear_winner, consensus, split}`, `confidence` 0–100, argument and risk lists, and per-speech scores 0–10 on clarity, logic, evidence, persuasiveness.

Prompts include `knowledge_block(state)` when documents exist, and the option list when structured mode has already run.

## Retrieval

`retrieve.py` scores each uploaded document by how often query tokens of length > 2 appear. It returns up to three snippets. No embeddings, no extra package. Uploads are decoded as UTF-8 and truncated to 20 000 characters each in `app.py`.

## Persistence and export

`save_debate` writes `data/debates/<debate_id>.json` after every UI sync. `list_debates` sorts by file mtime. JSON history is gitignored; `data/debates/.gitkeep` keeps the folder.

`debate_to_markdown` dumps settings, options, transcript, score table, and the report. `timeline_mermaid` is a left-to-right phase flowchart; the current `phase` is stroked.

## UI loop

`app.py` is a single page (not `st.navigation`). After **Start debate** it sets `auto_run` and `st.rerun`s. Each rerun, if `auto_run` and the debate is not done, it calls `advance` once and reruns again. **Pause** clears `auto_run`. That yields between LLM calls so the user can inject.

Provider dropdowns read Ollama tags through `@st.cache_data(ttl="30s")`.

## Quality gates

From `Makefile` / `.github/workflows/ci.yml`:

- `uv sync --all-groups --frozen`
- `ruff check`, `ruff format --check`, `ty check src/`
- `pytest` with branch coverage, fail under 80%
- `pip-audit`
- `prek` hooks job (Ruff, secrets, actionlint, zizmor)

Tests fake the chat client. They do not call live models or Streamlit.

## What is not here

No auth, no multi-user store, no PDF parse, no vector index, no crash-resume checkpointer (a loaded JSON file is the resume mechanism), no CLI that runs a debate.
