# How to use the debate system

Recipes for common jobs. For internals, see [technical.md](technical.md).

Repo: https://github.com/pypi-ahmad/multi-agent-debate-decision-system

## Run a first debate (Ollama)

Goal: see a transcript and a judgment on your machine.

1. Install [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com/). Pull one chat model, for example `ollama pull llama3.1:8b`.
2. In the repo root, double-click `run.cmd` (Windows) or run `uv sync --all-groups` then `uv run streamlit run app.py`.
3. Open http://localhost:8522
4. Turn **Fully local** on. Confirm the default provider is Ollama and a pulled model is in the dropdown.
5. Leave Mode on `open`. Set Debaters to 2 and Rounds to 1.
6. Enter a decision question, or pick one of the example pills.
7. Click **Start debate**. Wait until the status finishes.

You should see moderator and debater turns, then a **Decision report** with an outcome and a recommendation.

If the model list is empty, the Ollama daemon is not reachable at `OLLAMA_BASE_URL` (default `http://localhost:11434`). Pull a model, then refresh the page.

## Run a hosted model

Goal: use OpenAI, Agnes AI, or Google instead of Ollama.

1. Copy `.env.example` to `.env`.
2. Fill only the key for the provider you will use:

   | Provider | Env var | Models in the dropdown |
   | --- | --- | --- |
   | OpenAI | `OPENAI_API_KEY` | `gpt-5.6-luna`, `gpt-5.6-terra` (medium effort) |
   | Agnes AI | `AGNES_API_KEY` | `agnes-2.5-flash` |
   | Google | `GOOGLE_API_KEY` | `gemini-3.5-flash-lite`, `gemini-3.7-flash` |

3. Turn **Fully local** off.
4. Pick that provider as Default provider (and on each seat, if you override).
5. Start the debate. The Start button stays disabled until the matching key is set.

Optional: `OPENAI_BASE_URL` and `AGNES_BASE_URL` if you are not using the defaults in `.env.example`.

## Run a structured decision

Goal: get options and pros/cons before the hearing, then a report with confidence.

1. Set Mode to `structured`.
2. Enter the problem as a decision question (what should we do, not a yes/no chat prompt).
3. Start the debate.

The first two turns come from **Analyst**: a numbered option list, then a pros/cons write-up. Then the moderator opens the floor and the usual hearing runs. The judge report includes outcome (`clear_winner`, `consensus`, or `split`), confidence 0–100, strongest arguments, and key risks.

## Give agents different models

Goal: one persona on a local 8B model, the judge on a hosted model.

1. Leave **Fully local** off.
2. Under **Seats**, set each seat's persona, provider, and model.
3. Under **Moderator and judge**, set those two seats separately.
4. Confirm every chosen provider has its key in `.env` (or is Ollama).

If **Fully local** is on, every seat is forced to Ollama regardless of earlier dropdowns.

## Pause, inject, or demand evidence

Goal: steer a live hearing.

- **Pause** stops auto-advance.
- **One turn** runs the next graph node only.
- **Run remaining** continues until the judge finishes.
- **Inject** appends a Human turn. The next node is the moderator, who will see your note.
- **Ask for evidence** writes a moderator evidence request and gives the floor back to the last debater.

You cannot type into the page while a single LLM call is in flight. Pause first, then inject.

## Use uploaded documents

Goal: have speakers cite a spec or note you already have.

1. In the sidebar, upload `.txt`, `.md`, `.csv`, or `.json` (not PDF).
2. Start a new debate. Uploads attach to that run only.
3. Agents receive keyword hits from those files in their prompts.

This is substring overlap, not embeddings. Short, distinctive terms in the docs work better than vague ones.

## Continue an old debate

Goal: reopen a hearing you already ran.

1. After any start or step, the app writes `data/debates/<id>.json`.
2. In the sidebar **History** list, pick a row and click **Load debate**.
3. Use One turn or Run remaining if it was not finished.

JSON files in `data/debates/` are local and gitignored. Deleting a file removes it from History.

## Export the record

Goal: keep a copy outside the app.

After there is a transcript, click **Download markdown**. The file includes settings, options, transcript, scores, and the judgment.

To compare two personas, wait until at least two debaters have spoken, then use **Compare arguments**.

## Quality commands (developers)

```bash
uv sync --all-groups
uv run pytest
uv run ruff check
uv run ty check src/
```

Or `make test` / `make lint`.
