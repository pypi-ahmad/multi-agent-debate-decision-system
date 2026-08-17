# Technical reference

Internal machinery of `debate-decision-system 0.3.0`. How to use the app: [how-to-use.md](how-to-use.md). Cited architecture: [ARCHITECTURE.md](../ARCHITECTURE.md).

Repository: <https://github.com/pypi-ahmad/multi-agent-debate-decision-system>

## What this is

A Python package (`debate-decision-system` `0.3.0`) and a Streamlit application. One LangGraph hearing produces a structured verdict. Persistence is local SQLite plus a LanceDB vector store. There is no auth and no hosted API.

The console entry point `debate-decision-system` prints the version and exits. The product is Streamlit on port **8522**.

## Module map

| Module | Location | Purpose |
| --- | --- | --- |
| Navigation | `app.py` | `st.navigation`: four pages |
| Debate UI | `app_pages/debate.py` | Seats, step loop, inject, evidence, export, RAG toggle |
| History UI | `app_pages/history.py` | Search, continue, link, tag, archive |
| Analytics UI | `app_pages/analytics.py` | Charts, quality, win rates, simulation |
| Knowledge UI | `app_pages/knowledge.py` | Library upload, LanceDB stats, search test |
| State | `state.py` | `DebateState` TypedDict, all literal types, `Turn`, `Verdict`, `DebaterSpec` |
| Graph | `graph.py` | `build_graph`, `advance`, `initial_state`, `inject_human`, `request_evidence` |
| Structure nodes | `agents/structure.py` | `options_node`, `pros_cons_node` |
| Moderator | `agents/moderator.py` | `moderator_node`, `should_judge` |
| Debater | `agents/debater.py` | `debater_node` |
| Huddle | `agents/huddle.py` | `huddle_node` |
| Judge | `agents/judge.py` | `judge_node` |
| Tools | `tools.py` | `tools_node`, `calculator`, `run_code`, `wikipedia`, `web_search`, `execute_tool` |
| Personas | `personas.py` | `PERSONAS`, `assign_personas`, `select_personas` |
| Teams | `teams.py` | `TEAM_TEMPLATES`, seat helpers, `public_voice` |
| Memory | `memory.py` | SQLite `data/decisions.db`, `save_debate`, `search_decisions`, `archive_decision` |
| History re-export | `history.py` | Re-exports `save_debate`, `load_debate`, `list_debates`, `search_decisions` |
| RAG pipeline | `rag/pipeline.py` | `context_for_state`, `index_decision`, chunking |
| RAG embeddings | `rag/embeddings.py` | `embed_text`, backend selection |
| RAG retriever | `rag/retriever.py` | `hybrid_search`, `rewrite_query` |
| RAG reranker | `rag/reranker.py` | `rerank`, `compress`, `llm_rerank` |
| Vector store | `rag/vectorstore.py` | `Chunk`, `upsert_chunks`, `delete_source` |
| Analytics | `analytics.py` | Overlap, participation, circular pairs, strength series, `quality_report` |
| Export | `export.py` | `debate_to_markdown`, `timeline_mermaid` |
| Config | `config.py` | All env vars and constants |
| LLM | `llm.py` | `get_chat_model`, provider dispatch |
| Documents | `documents.py` | Text, PDF (`pypdf`), ZIP loading |
| Retrieve | `retrieve.py` | Keyword `retrieve` (no RAG path) |

The UI calls `advance()`. It never builds a provider client directly.

## State: DebateState

`DebateState` is a `TypedDict(total=False)` in `state.py`. All fields are optional at the type level; the graph treats absent fields as falsy defaults.

### Scalar fields

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `debate_id` | `str` | `uuid4().hex[:12]` | Set by `initial_state` |
| `topic` | `str` | — | Stripped of whitespace |
| `mode` | `"open" \| "structured"` | `"open"` | Structured adds options + pros/cons phases |
| `provider` | `Provider` | — | `"Ollama" \| "OpenAI" \| "Agnes AI" \| "Google"` |
| `model` | `str` | — | Default model for debaters |
| `moderator_provider` | `Provider` | same as `provider` | |
| `moderator_model` | `str` | same as `model` | |
| `judge_provider` | `Provider` | same as `provider` | |
| `judge_model` | `str` | same as `model` | |
| `temperature` | `float` | `0.4` | 0.0–1.2; stripped for `gemini-3.7-flash` |
| `speaking_order` | `"sequential" \| "reverse" \| "random"` | `"sequential"` | |
| `local_only` | `bool` | `False` | Rewrites all seats and roles to Ollama |
| `grounding` | `"open" \| "grounded"` | `"open"` | Controls tool allowlist |
| `awaiting_speech` | `bool` | `False` | Set by `tools_node`; cleared by `debater_node` |
| `huddle_done` | `bool` | `False` | Cleared after each public speech |
| `huddle_index` | `int` | `0` | Index into current seat's member list |
| `max_rounds` | `int` | `2` | Total rounds before judge is called |
| `next_speaker` | `int` | `0` | Index into `debaters` |
| `speeches_done` | `int` | `0` | Public debater speeches; judge fires when `speeches_done >= max_rounds * len(debaters)` |
| `phase` | `"options" \| "pros_cons" \| "debate" \| "judge"` | `"options"` or `"debate"` | |
| `pros_cons` | `str` | `""` | Produced by `pros_cons_node` |
| `rag_enabled` | `bool` | `True` | Controls `tool:rag` citation turn |
| `batch_id` | `str` | — | Reserved for simulation batches |

### List fields

| Field | Type | Reducer | Notes |
| --- | --- | --- | --- |
| `transcript` | `list[Turn]` | `operator.add` | Accumulates; never overwritten |
| `errors` | `list[str]` | `operator.add` | Non-fatal error strings |
| `options` | `list[str]` | replace | Options proposed by `options_node` |
| `debaters` | `list[DebaterSpec]` | replace | Seat configurations |
| `documents` | `list[Document]` | replace | Uploaded documents |
| `pinned_ids` | `list[str]` | replace | Decision IDs pinned for RAG context |

### Nested types

```python
class Turn(TypedDict):
    role: Literal["moderator", "debater", "judge", "human", "tool", "huddle"]
    name: str
    content: str


class DebaterSpec(TypedDict, total=False):
    name: str
    style: str
    instructions: str
    provider: Provider
    model: str
    kind: Literal["agent", "team"]
    members: list[TeamMember]


class TeamMember(TypedDict, total=False):
    name: str
    style: str
    instructions: str
    provider: Provider
    model: str
    is_leader: bool


class Verdict(TypedDict, total=False):
    winner: str
    recommendation: str
    rationale: str
    scores: list[SpeechScore]
    outcome: Literal["clear_winner", "consensus", "split"]
    confidence: int  # 0–100
    strongest_arguments: list[str]
    key_risks: list[str]


class SpeechScore(TypedDict):
    speaker: str
    clarity: int
    logic: int
    evidence: int
    persuasiveness: int


class Document(TypedDict):
    name: str
    text: str
```

## Runtime and providers

`.env` loads from the project root. OS env wins (`override=False`).

| Provider | Models | Required env | Optional env | Client | Timeout |
| --- | --- | --- | --- | --- | --- |
| Ollama | tags from `GET /api/tags` | — | `OLLAMA_BASE_URL` (default `http://localhost:11434`) | `ChatOllama` | 120 s |
| OpenAI | `gpt-5.6-luna` (effort `medium`) | `OPENAI_API_KEY` | `OPENAI_BASE_URL` (default `https://api.openai.com/v1`) | `ChatOpenAI` | 90 s |
| Agnes AI | `agnes-2.5-flash` | `AGNES_API_KEY` | `AGNES_BASE_URL` (default `https://apihub.agnes-ai.com/v1`) | `ChatOpenAI` @ base URL | 90 s |
| Google | `gemini-3.5-flash-lite`, `gemini-3.7-flash` | `GOOGLE_API_KEY` | — | `ChatGoogleGenerativeAI` | 90 s |

`local_only=True` rewrites every seat, moderator, and judge to Ollama before `initial_state` builds the debater list.

> **`gemini-3.7-flash` strips sampling parameters.** `temperature`, `top_p`, and `top_k` are removed before the request is sent (`GOOGLE_NO_SAMPLING` in `config.py`, applied in `llm.py`). The temperature slider in the UI has no effect for this model.

## Graph execution

### Wiring

```
START → route_start → [options | moderator]
options → pros_cons → moderator
moderator → route_after_moderator → [tools | judge]
tools → huddle → debater → moderator
judge → END
```

`debate_graph = build_graph()` compiles the graph at import time. The UI does not call `debate_graph.invoke` — it calls `advance()` one step at a time.

### `next_action(state) → str`

Determines which node to call next without mutating state. Rules in order:

1. `debate_done(state)` → `"end"` — verdict present, or last turn role is `"judge"`
2. `phase == "options"` → `"options"`
3. `phase == "pros_cons"` → `"pros_cons"`
4. `phase == "judge"` → `"judge"`
5. `should_judge(state)` OR transcript empty OR last turn is `debater`/`human` → `"moderator"`
6. `awaiting_speech` OR last turn is `tool`/`huddle`, AND current seat is a team AND `huddle_done` is False → `"huddle"`
7. `awaiting_speech` OR last turn is `tool`/`huddle` → `"debater"`
8. Last turn is `moderator` (not Analyst) → `"tools"`
9. Otherwise → `"end"`

### `advance(state) → DebateState`

Dispatches to the node returned by `next_action`, calls `apply_update`, and returns the new state. The UI calls `advance` in a loop until `debate_done` or the user pauses.

### Helper functions

| Function | Purpose |
| --- | --- |
| `inject_human(state, text)` | Appends `Turn(role="human")`; does not increment `speeches_done` |
| `request_evidence(state)` | Finds last public debater, retargets `next_speaker`, appends a moderator evidence-request turn |
| `debate_done(state)` | Returns `True` if verdict present or last turn is `judge` |
| `apply_update(state, update)` | Merges update dict; appends to `transcript`/`errors`, replaces other fields |

## Agents (nodes)

Each node returns a `dict` of state updates. `apply_update` merges them, appending to `transcript` and `errors`.

| Node | Function | Key inputs read | Key outputs written |
| --- | --- | --- | --- |
| Options | `options_node` | `topic`, `provider`, `model` | `options: list[str]`, `phase: "pros_cons"` |
| Pros/cons | `pros_cons_node` | `options`, `topic`, `provider`, `model` | `pros_cons: str`, `phase: "debate"` |
| Moderator | `moderator_node` | `speeches_done`, `max_rounds`, `debaters`, `transcript` | `transcript: [Turn]`, `phase` update when quota met |
| Tools | `tools_node` | `transcript`, `grounding`, `rag_enabled`, `debaters[next_speaker]` | `transcript: [tool turns]`, `awaiting_speech: True` |
| Huddle | `huddle_node` | `debaters[next_speaker].members`, `huddle_index`, `transcript` | `transcript: [huddle Turn]`, `huddle_index += 1` or `huddle_done: True` |
| Debater | `debater_node` | `debaters[next_speaker]`, `transcript`, `temperature`, huddle notes | `transcript: [debater Turn]`, `speeches_done += 1`, `next_speaker` advanced, `huddle_done: False` |
| Judge | `judge_node` | `transcript[-24:]`, `debaters`, `topic` | `verdict: Verdict`, `phase: "judge"` |

`judge_node` passes at most the 24 most recent transcript turns to the LLM to bound prompt size.

## Tools

| Tool | Available in | Implementation | Max calls |
| --- | --- | --- | --- |
| `calculator` | open + grounded | `ast.parse` + `_eval_num`; operators `+ - * / // ** %` | 2 per turn |
| `code` | open + grounded | `ast.parse` + `_eval_code`; all `math.*` plus `abs min max sum round len` | 2 per turn |
| `wikipedia` | open only | `GET en.wikipedia.org/api/rest_v1/page/summary/{title}` | 2 per turn |
| `web_search` | open only | DuckDuckGo Instant Answer JSON (`api.duckduckgo.com`) | 2 per turn |
| `docs` | open + grounded | `retrieve()` keyword overlap + RAG when enabled | 2 per turn |

`GROUNDED_TOOLS = frozenset({"calculator", "code", "docs"})` — `wikipedia` and `web_search` are blocked when `grounding == "grounded"`.

`tools_node` calls `plan_tools` (structured output → `ToolPlan`) then `run_tool_calls` (capped at 2). After tool turns, if `rag_enabled`, `_rag_citation_turn` appends a `tool:rag` turn from `context_for_state`.

## Personas

Ten built-in personas in `personas.py`. `assign_personas(n)` returns the first `n` (clamped to 2–8). `select_personas(names)` resolves by name; unknown names are silently skipped.

| # | Name | Style | Instructions (first sentence) |
| --- | --- | --- | --- |
| 1 | Pragmatist | ships the smallest thing that works | Optimize for what can ship this quarter. |
| 2 | Skeptic | hunts hidden failure modes | Assume the popular option is wrong until proven. |
| 3 | First-principles | rebuilds from constraints | Ignore slogans. Start from physical, legal, and budget constraints. |
| 4 | Devil's advocate | argues the opposite of the room | Take the side that is losing or unstated. |
| 5 | Ethicist | tracks stakeholders and second-order harm | Ask who pays, who consents, and what happens to people not in the room. |
| 6 | Operator | asks who does the work on Monday | Translate every argument into staffing, process, and failure recovery. |
| 7 | Optimistic | looks for upside and reversible bets | Name the best plausible outcome and the cheapest test that would unlock it. |
| 8 | Data-driven | demands numbers and base rates | Refuse claims that have no metric, sample, or comparison. |
| 9 | Risk-averse | minimizes downside and tail risk | Ask what happens if we are wrong. |
| 10 | Creative | offers a third option the room did not name | Do not only pick A or B. Propose one concrete alternative that changes a constraint. |

## Teams

A seat with `kind == "team"` runs a private huddle before its public speech. `public_voice(seat)` builds a `DebaterSpec` from the leader member; the public name is the seat's name, not the leader's persona name.

### Templates

| Template | Members (index 0 = leader) |
| --- | --- |
| Engineering | Pragmatist (L), First-principles, Operator |
| Product | Optimistic (L), Data-driven, Creative |
| Business | Pragmatist (L), Risk-averse, Operator |
| Security | Skeptic (L), Risk-averse, First-principles |
| Devil's Advocate | Devil's advocate (L), Skeptic, Ethicist |

`members_from_template(name, provider, model)` builds the member list from `TEAM_TEMPLATES`. `is_leader` is `True` for index 0.

`huddle_members(seat)` returns members where `is_leader` is falsy. `leader_member(seat)` returns the first member with `is_leader=True`, or `members[0]` if none is marked, or a fallback derived from the seat spec if the list is empty.

## RAG pipeline

### Chunking

Source text is split at paragraph boundaries. `CHUNK_SIZE = 700` characters, `CHUNK_OVERLAP = 100`. Content hash (Blake2b-128) is used for incremental upsert — unchanged chunks are not re-embedded.

### Pipeline (`rag/pipeline.py`)

`context_for_state(state) → RagResult`:

1. **Rewrite** — `rewrite_query` reformulates the topic for retrieval quality.
2. **Hybrid search** — `hybrid_search` combines dense LanceDB vector search with BM25 keyword search, fused with Reciprocal Rank Fusion (RRF).
3. **Rerank** — feature-based `rerank`; optional `llm_rerank` for deeper scoring.
4. **Compress** — `compress` trims each passage to the most relevant sentences.
5. **Cite** — `citation_for(chunk)` produces `[source: type:name#chunk_index]`.

Results are pulled from both `session` (current debate uploads) and `longterm` (Knowledge library + indexed decisions) collections.

### Collections

| Collection | Contents | When populated |
| --- | --- | --- |
| `session` | Documents uploaded for the current debate | Debate UI upload |
| `longterm` | Knowledge library + past saved decisions | Knowledge page index; `save_debate` → `index_decision` |

`delete_decision(debate_id)` calls `delete_source("decision", debate_id)` to remove those vectors from `longterm`.

Multi-hop context follows `decision_links` — linked decisions are included in the RAG context.

### Embeddings (`rag/embeddings.py`)

`RAG_EMBED_BACKEND` (default `auto`):

| Value | Behaviour |
| --- | --- |
| `auto` | Tries Ollama with `RAG_EMBED_MODEL` (default `nomic-embed-text`); also tries `bge-small` as a fallback; falls back to hashed backend if no embed model responds |
| `hash` | Always uses deterministic 256-d hashed embeddings — no Ollama required, no semantic similarity |

Vector store path: `data/lancedb/` (`STORE_PATH`).

## Memory

Database: `data/decisions.db` (SQLite). Created automatically on first `save_debate` call. FTS5 virtual table `decisions_fts` is rebuilt automatically if row counts diverge.

### `decisions` table (23 columns)

| Column | Type | Notes |
| --- | --- | --- |
| `debate_id` | TEXT PK | 12-char hex UUID fragment |
| `topic` | TEXT | |
| `created_at` | TEXT | ISO-8601 UTC; set on first insert, preserved on upsert |
| `updated_at` | TEXT | ISO-8601 UTC; updated on every save |
| `phase` | TEXT | Last phase at save time |
| `mode` | TEXT | `open` or `structured` |
| `status` | TEXT | `in_progress` \| `decided` \| `archived` |
| `recommendation` | TEXT | From verdict |
| `confidence` | INTEGER | 0–100, from verdict |
| `outcome` | TEXT | `clear_winner` \| `consensus` \| `split` |
| `winner` | TEXT | Winning seat name |
| `participants` | TEXT | JSON list of seat names |
| `agent_models` | TEXT | JSON dict — `"seat" → "provider/model"` |
| `key_arguments` | TEXT | JSON list (for + against combined) |
| `arguments_for` | TEXT | JSON list from `verdict.strongest_arguments` |
| `arguments_against` | TEXT | JSON list from `verdict.key_risks` |
| `rationale` | TEXT | Free-text rationale |
| `transcript` | TEXT | Flat `name: content` text (searchable) |
| `tags` | TEXT | JSON list |
| `category` | TEXT | |
| `notes` | TEXT | |
| `archived` | INTEGER | `0` or `1`; default `0` |
| `state_json` | TEXT NOT NULL | Full `DebateState` JSON — enables full resume |

`decision_links`: undirected pairs `(left_id, right_id)` — primary key is the sorted pair.

`decisions_fts` (FTS5 virtual table): `debate_id UNINDEXED`, `topic`, `recommendation`, `rationale`, `arguments`, `notes`, `participants`, `tags`, `category`, `transcript`.

### Key functions

| Function | Purpose |
| --- | --- |
| `save_debate(state, *, notes, tags, category)` | Upsert on `debate_id`; calls `index_decision` for RAG; preserves `created_at`, notes, tags, category from prior row |
| `load_debate(debate_id)` | Reads `state_json`; falls back to legacy `data/debates/<id>.json`, migrates it to SQLite |
| `search_decisions(query, *, outcome, status, since, until, tag, category, min_confidence, include_archived)` | FTS5 AND → OR → LIKE fallback; archived excluded by default |
| `archive_decision(debate_id, *, archived)` | Toggle `archived` flag; does not delete |
| `delete_decision(debate_id)` | Removes row, FTS entry, and LanceDB vectors |
| `update_decision_meta(debate_id, *, notes, tags, category)` | Update metadata without touching `state_json` |
| `link_decisions(left_id, right_id)` | Upsert undirected link (sorted pair) |
| `related_ids(debate_id)` | Return IDs linked to this debate (both directions) |
| `relevant_decisions(topic, *, exclude_id, limit)` | FTS search filtered to `decided`, used for RAG context |

Status is set to `"decided"` when the verdict has a recommendation or winner, or when the last transcript turn is `judge`. Otherwise `"in_progress"`.

## Analytics

All functions are pure — they read state but do not mutate it.

| Function | Purpose | Key detail |
| --- | --- | --- |
| `token_overlap(left, right)` | Jaccard similarity on words longer than 2 chars | Returns 0.0–1.0 |
| `participation(state)` | Count `debater` + `huddle` turns per name | Returns `Counter` as dict |
| `participation_balance(counts)` | `min / max` turn counts | 1.0 = perfectly balanced |
| `circular_pairs(state)` | Consecutive public speeches with overlap ≥ 0.55 | Returns list of `{left, right, overlap}` |
| `strength_series(state)` | Mean of `[clarity, logic, evidence, persuasiveness]` per scored speech | Reads `verdict.scores` |
| `mean_strength(state)` | Average of `strength_series` | `None` if no scores |
| `strength_over_time(states)` | Average `mean_strength` grouped by date key | For trend charts |
| `quality_report(state)` | Participation balance + circular flags + mean score axes + LLM summary | Structured dict |
| `reset_for_rerun(state)` | Deep copy with new `debate_id`, empty transcript | Does not call providers |
| `run_until_done(state, advance_fn)` | Loop `advance_fn` until `debate_done` | Used by Analytics simulation |

Circular speech flag threshold: `_OVERLAP_FLAG = 0.55`.

## Export

| Function | Output | Notes |
| --- | --- | --- |
| `debate_to_markdown(state)` | Full Markdown: settings, options, pros/cons, full transcript, score table, judgment, key risks | Available from Debate page and History **Export record** |
| `timeline_mermaid(state)` | Mermaid `flowchart LR` with phases; current phase highlighted `stroke:#0969da,stroke-width:3px` | Open-mode steps: problem → debate → judge. Structured: problem → options → pros_cons → debate → judge |

## Configuration reference

All constants are in `config.py`. Functions (e.g. `openai_api_key()`) read live env vars at call time; module-level names (e.g. `OPENAI_API_KEY`) are snapshots at import time — prefer the functions in application code.

| Constant | Default | Notes |
| --- | --- | --- |
| `MIN_DEBATERS` | `2` | |
| `MAX_DEBATERS` | `8` | |
| `DEFAULT_DEBATERS` | `2` | |
| `MIN_ROUNDS` | `1` | |
| `MAX_ROUNDS` | `6` | |
| `DEFAULT_ROUNDS` | `2` | |
| `DEFAULT_TEMPERATURE` | `0.4` | |
| `MIN_TEMPERATURE` | `0.0` | |
| `MAX_TEMPERATURE` | `1.2` | |
| `DEFAULT_SPEAKING_ORDER` | `"sequential"` | |
| `SPEAKING_ORDERS` | `("sequential", "reverse", "random")` | |
| `MIN_TEAM_MEMBERS` | `2` | |
| `MAX_TEAM_MEMBERS` | `4` | |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | |
| `REASONING_TIMEOUT_SECONDS` | `90` | OpenAI, Agnes AI, Google |
| `DEFAULT_OPENAI_BASE_URL` | `https://api.openai.com/v1` | |
| `DEFAULT_AGNES_BASE_URL` | `https://apihub.agnes-ai.com/v1` | |
| `DEFAULT_OLLAMA_BASE_URL` | `http://localhost:11434` | |
| `OPENAI_MODELS` | `("gpt-5.6-luna",)` | |
| `OPENAI_REASONING_EFFORT` | `"medium"` | |
| `AGNES_MODEL` | `"agnes-2.5-flash"` | |
| `GOOGLE_MODELS` | `("gemini-3.5-flash-lite", "gemini-3.7-flash")` | |
| `GOOGLE_NO_SAMPLING` | `frozenset({"gemini-3.7-flash"})` | Temperature stripped silently |
| `RAG_EMBED_MODEL` | `"nomic-embed-text"` | Override with `RAG_EMBED_MODEL` env var |
| `RAG_EMBED_BACKEND` | `"auto"` | Override with `RAG_EMBED_BACKEND` env var |

## Quality gates

```bash
make lint    # ruff format --check + ruff check + ty check src/
make test    # pytest --cov=debate_decision_system --cov-fail-under=80
make audit   # pip-audit
```

Or individually:

```bash
uv run ruff format --check
uv run ruff check
uv run ty check src/
uv run pytest
```

Coverage must stay at or above **80%**. Tests use fake chat clients — do not add live-LLM end-to-end tests.

CI runs on every push/PR to `main`: frozen `uv sync`, quality (Ruff + ty + pytest), hooks (pre-commit).

## Not here

No auth, no multi-user server, no unrestricted `exec`, no CLI that runs a debate end-to-end.
