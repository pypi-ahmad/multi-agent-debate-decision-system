# How to use

Step-by-step recipes for the Multi-Agent Debate Decision System. For internals see [technical.md](technical.md).

Repository: <https://github.com/pypi-ahmad/multi-agent-debate-decision-system>

## Requirements

- [uv](https://docs.astral.sh/uv/) 0.11 or later
- Python 3.11, 3.12, or 3.13 (uv installs it automatically)
- [Ollama](https://ollama.com/) for fully local models, or an API key for a hosted provider
- Windows (native cmd/Explorer — not WSL or Docker) or native Linux

## Launch for the first time

Clone the repository, then run the launcher for your OS.

```bash
git clone https://github.com/pypi-ahmad/multi-agent-debate-decision-system.git
cd multi-agent-debate-decision-system
```

| OS | Command |
| --- | --- |
| Windows | Double-click `run.cmd` or run it in cmd |
| Linux | `chmod +x run.sh && ./run.sh` |

The launcher does the following on first run:

1. Installs uv if missing (via the official installer)
2. Creates `.venv` at the repo root
3. Syncs all dependencies from the lockfile (`uv sync`)
4. Copies `.env.example` → `.env` when no `.env` exists
5. Creates `data/debates/` and `data/lancedb/`
6. Starts Streamlit at `http://localhost:8522`

Open [http://localhost:8522](http://localhost:8522) in your browser.

> [!IMPORTANT]
> Do not run inside WSL or Docker — the launchers target native environments only.

On subsequent runs the launcher skips setup steps that are already done and goes straight to launching Streamlit.

## Run your first debate

This route needs no API key.

1. Install a local model: `ollama pull llama3.1:8b`
2. Start the app
3. On the **Debate** page, leave **Fully local** toggled on
4. Pick the model from the dropdown (e.g. `llama3.1:8b`)
5. Set seats to **2**, rounds to **1**, mode to **open**
6. Type a decision question in the topic field
7. Click **Start debate**, then **Step** to advance one turn at a time — or **Run** to run to completion

> [!TIP]
> If the model dropdown is empty, Ollama is not running or is unreachable at `OLLAMA_BASE_URL` (default `http://localhost:11434`). Start Ollama first.

## Use a hosted model

Add your API key to `.env` or your OS environment, then turn **Fully local** off.

| Provider | Env var | Model | Optional base-URL env var | Default base URL |
| --- | --- | --- | --- | --- |
| OpenAI | `OPENAI_API_KEY` | `gpt-5.6-luna` | `OPENAI_BASE_URL` | `https://api.openai.com/v1` |
| Agnes AI | `AGNES_API_KEY` | `agnes-2.5-flash` | `AGNES_BASE_URL` | `https://apihub.agnes-ai.com/v1` |
| Google | `GOOGLE_API_KEY` | `gemini-3.5-flash-lite` or `gemini-3.7-flash` | — | — |

OS environment wins over `.env`. Restart the app after editing `.env`.

> [!WARNING]
> `gemini-3.7-flash` ignores the temperature slider. Sampling parameters (`temperature`, `top_p`, `top_k`) are stripped automatically. Use `gemini-3.5-flash-lite` if you need temperature control.

## Run a structured debate

Structured mode adds two pre-debate phases: the moderator enumerates options, then an analyst produces a pros/cons summary, before the hearing begins.

1. Set **Mode** to `structured`
2. Start the debate
3. Advance through: **options** → **pros/cons** → **hearing** → **judgment**

Use structured mode when your question has multiple discrete options you want evaluated explicitly before the debate starts.

## Assign specific personas

The app has ten built-in personas. Without explicit selection, `assign_personas` picks the first N in order.

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

In the **Debate** page, expand the **Seats** section. Each seat shows a persona dropdown — choose one from the list, or leave it for auto-assignment.

Each seat can also override the default provider and model independently, so you can mix Ollama and hosted models in a single debate.

## Use a team seat

A team seat runs a private huddle among its members before the leader speaks publicly. Huddle turns appear in the transcript with role `huddle` and a combined name (`"Team / PersonaName"`). Only the leader's public speech appears under the team's seat name.

1. Set a seat's type to **Team**
2. Pick a template from the dropdown

| Template | Members (first = leader by default) |
| --- | --- |
| Engineering | Pragmatist, First-principles, Operator |
| Product | Optimistic, Data-driven, Creative |
| Business | Pragmatist, Risk-averse, Operator |
| Security | Skeptic, Risk-averse, First-principles |
| Devil's Advocate | Devil's advocate, Skeptic, Ethicist |

3. Optionally mark a different member as **Leader**
4. During the debate, the app advances through each huddle member before the leader's public speech

## Ground speeches in documents

Grounded mode restricts tool use to `calculator`, `code`, and `docs` (Wikipedia and web search are blocked), and asks debaters to cite uploaded sources.

1. On the **Debate** page, open the **Knowledge** section
2. Toggle **Grounded** on
3. Click **Upload** and add `.pdf`, `.md`, `.py`, `.txt`, or `.zip` files
4. Start the debate

Speeches in grounded mode must include `[source: …]` citations. If a speech has no `[` character, the debater is prompted once to add a citation.

## Build and search the RAG library

The **Knowledge** page manages a long-term vector library, separate from per-debate uploads.

1. Open the **Knowledge** page
2. Upload documents in the **Library** section — these are indexed into the `longterm` LanceDB collection and persist across debates
3. Use **Search test** to verify a query returns relevant passages before starting a debate
4. On the Debate page, enable **RAG** — the system retrieves from both the session collection (current debate uploads) and the longterm collection (library + past decisions)

Past decided debates are automatically indexed into `longterm` when saved. Use **Pinned decisions** on the Debate page to include specific past decisions in every RAG query for the current debate.

## Pause and inject a human note

You can pause the debate at any point and inject a message as a human participant.

1. During a debate, click **Pause**
2. Type your message in the **Inject** field
3. Click **Inject** — a `human` turn is appended to the transcript
4. Click **Step** or **Run** to continue

Injected human turns do not increment `speeches_done`, so they do not count toward the round quota.

## Ask a debater for evidence

If you want a debater to support a claim with a citation:

1. After a debater speaks, click **Ask for evidence**
2. The moderator issues an evidence-request turn targeting the last public debater
3. That seat takes the next turn and must cite a source, metric, or uploaded document

The evidence request does not count toward `speeches_done` either.

## Continue a past debate

Every debate is stored in `data/decisions.db` as full state JSON.

1. Open **Decision history**
2. Search or filter to find the debate (use the search box, outcome filter, status filter, or date range)
3. Click **Continue debate** — the full `DebateState` is restored from `state_json`
4. Advance from where it left off

Debates with status `in_progress` can always be continued. Decided debates can also be re-opened and extended.

## Search, tag, and archive past debates

### Search

The search box in **Decision history** runs FTS5 full-text search (AND → OR → LIKE fallback) across topic, recommendation, rationale, arguments, notes, tags, category, and transcript.

### Filters

| Filter | Accepted values |
| --- | --- |
| Outcome | `clear_winner`, `consensus`, `split` |
| Status | `in_progress`, `decided`, `archived` |
| Since / Until | ISO date `YYYY-MM-DD` |
| Tag | Any tag string (partial match) |
| Category | Exact match |
| Min confidence | 0–100 |

### Tags, category, and notes

Click **Edit** on any history record to add free-text tags, a category label, or notes. All three fields are indexed and searchable.

### Archiving

Click **Archive** to hide a record from the default view (`archived = 1`). Archived debates are not deleted — use the **Archived** status filter to show them. Click **Unarchive** to restore.

### Linking

Use **Link** to create an undirected relationship between two debates. Linked debates are pulled into each other's RAG context when RAG is enabled.

## Export a debate

Two export formats are available from the **Debate** page and the **History** page.

| Export | What you get |
| --- | --- |
| **Export record** (Markdown) | Settings, options, pros/cons, full transcript, speech score table, judgment, strongest arguments, key risks |
| **Mermaid timeline** | `flowchart LR` diagram showing phase order; current phase highlighted in blue |

The Mermaid timeline renders inline in the Debate page after the debate finishes. The Markdown export downloads as a file.

## Read the analytics page

The **Analytics** page shows aggregate stats across all saved debates.

| Metric | What it measures |
| --- | --- |
| Win rates | Which seats or personas win most often across `decided` debates |
| Participation balance | `min / max` speech count per seat — 1.0 means all seats spoke equally |
| Circular speech flags | Consecutive public speeches with Jaccard token overlap ≥ 0.55 — signals repetition |
| Strength over time | Mean score (clarity + logic + evidence + persuasiveness ÷ 4) averaged by date |
| Quality report | Per-debate: participation counts, circular flags, mean score axes, one-paragraph summary |

**Simulation** (in the Analytics page) runs `run_until_done` — loops `advance` without pausing, useful for batch testing persona combinations.
