# How to use the debate system

Recipes for common jobs. Internals: [technical.md](technical.md).

Repo: https://github.com/pypi-ahmad/multi-agent-debate-decision-system

## Run a first debate (Ollama)

1. Install [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com/). Pull a chat model, e.g. `ollama pull llama3.1:8b`.
2. Windows: double-click `run.cmd`. Linux: `./run.sh`. Either creates repo-root `.venv` with uv and runs inside it.
3. Open http://localhost:8522
4. On **Debate**, turn **Fully local** on. Pick an Ollama model.
5. Leave Mode on `open`. Seats: 2 agents, 1 round.
6. Enter a decision question. Click **Start debate**.

You should see moderator and speaker turns, then a **Decision report**.

Empty model list means Ollama is not reachable at `OLLAMA_BASE_URL` (default `http://localhost:11434`).

## Use a hosted model

1. Copy `.env.example` to `.env`. Fill one key:

   | Provider | Required env | Optional env | Dropdown |
   | --- | --- | --- | --- |
   | OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` — point to any OpenAI-compatible endpoint (default `https://api.openai.com/v1`) | `gpt-5.6-luna` (medium effort) |
   | Agnes AI | `AGNES_API_KEY` | `AGNES_BASE_URL` — default `https://apihub.agnes-ai.com/v1` | `agnes-2.5-flash` |
   | Google | `GOOGLE_API_KEY` | — | `gemini-3.5-flash-lite`, `gemini-3.7-flash` |

   > [!NOTE]
   > `gemini-3.7-flash` does not accept a temperature setting. The temperature slider has no effect for this model.

2. Turn **Fully local** off. Pick that provider. Start.

## Run a structured decision

Set Mode to `structured`. The first turns are **Analyst** (options, then pros/cons). Then the hearing and a report with confidence.

## Use a team seat

1. Under Seats, set Type to `team`.
2. Pick Engineering, Product, Business, Security, or Devil's Advocate.
3. Mark one member as Leader.

Members huddle in expanders. The public turn is the team name with a **team** badge. You can mix agent seats and team seats.

## Personas

Ten built-in personas are available. The UI shows a dropdown per seat; without an explicit selection, the first N personas in the list are assigned in order.

| Name | Style |
| --- | --- |
| Pragmatist | ships the smallest thing that works |
| Skeptic | hunts hidden failure modes |
| First-principles | rebuilds from constraints |
| Devil's advocate | argues the opposite of the room |
| Ethicist | tracks stakeholders and second-order harm |
| Operator | asks who does the work on Monday |
| Optimistic | looks for upside and reversible bets |
| Data-driven | demands numbers and base rates |
| Risk-averse | minimizes downside and tail risk |
| Creative | offers a third option the room did not name |

You can also assign a different provider and model to each seat independently using the per-seat dropdowns in the Seats panel.

## Ground speeches in documents

1. Set Knowledge to `grounded`.
2. Upload `.pdf`, `.md`, `.py`, `.txt`, or a `.zip` of a folder.
3. Leave **RAG** on if you want LanceDB retrieve plus citations in `tool:rag` turns.
4. Start. Agents may use **docs**, calculator, and code only. Speeches should include `[source:…]` or `[filename]`.

**Open** knowledge also allows Wikipedia and DuckDuckGo. Tool results appear as `tool:…` turns.

## Build a long-term knowledge library

1. Open **Knowledge**.
2. Upload files and click **Index uploads**.
3. Use **Search test** to see retrieved chunks and citations.
4. Check chunk count, source count, and last updated.

Optional: `ollama pull nomic-embed-text` so RAG uses Ollama embeddings instead of the hashed fallback.

Debate uploads stay short-term (`session`) unless you index them here (`longterm`).

## Pause, inject, demand evidence

Pause → **Inject** a human note, or **Ask for evidence** (returns the floor to the last public speaker). **One turn** / **Run remaining** step the graph.

**Pin past decisions into RAG** (sidebar) forces those hearings into retrieve.

## Search and continue a past decision

1. Open **Decision history**.
2. Search (e.g. “Why did we choose SQLite last month?”). Filter status, outcome, date, confidence, tag, category. Status options include `archived`.
3. **Continue debate** resumes the graph. **Re-run with new settings** clears the transcript and keeps seats.
4. **Link decisions** ties related hearings.
5. Open a record to edit its **Notes**, **Tags** (multi-select), and **Category**, then click **Save notes and tags** to persist them to SQLite.
6. Use the **Archive** / **Unarchive** button to hide a decision from the default view without deleting it.
7. **Export record** downloads a Markdown summary. The debate page also exports a **Mermaid timeline** diagram alongside the Markdown for finished debates.

Storage is local SQLite: `data/decisions.db` (gitignored).

## Study reasoning patterns

1. Finish at least one debate.
2. Open **Analytics**.
3. Read win rates, participation, circular-speech flags, strength over time, and the quality report.
4. **Run simulation**: pick models and 2–5 runs. Each run is saved in history under a batch id.

Simulation calls live models. Keep runs small.

## Developer checks

```bash
uv run pytest
uv run ruff check
uv run ty check src/
```
