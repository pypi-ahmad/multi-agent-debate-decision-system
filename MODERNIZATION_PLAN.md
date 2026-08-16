# Modernization plan — debate-decision-system

Cites [`ARCHITECTURE.md`](ARCHITECTURE.md). Forward-looking only.

## 1. Executive summary

This checkout is **already on the target stack** (Python ≥3.11, uv lockfile, `uv_build`, Ruff, ty, pytest 80%, pip-audit, prek, SHA-pinned CI). Do **not** rewrite Streamlit, LangGraph, or SQLite. Plan is **leave-in-place** plus small lit-regime hardening: close coverage holes, keep `history.py` as a shim, freeze seam tests, confirm CI is *enforced*. Scope: XS–S. A multi-phase stack rewrite is over-engineering.

## 2. Current state assessment

From [`ARCHITECTURE.md`](ARCHITECTURE.md) Part 1.

| Item | Now |
| --- | --- |
| Language | Python ≥3.11, local pin 3.13 |
| App | Streamlit `st.navigation` + `app_pages/` |
| Graph | LangGraph nodes + hand `advance()` stepper |
| Memory | SQLite + FTS5 + `state_json` |
| Quality | 33 tests, 82% cov, ruff/ty/audit green this session |
| Deploy | Local process, port 8522, no container |
| Pain | Coverage thin on `documents`/`llm`/`tools`/`agents`; compiled `debate_graph` unused; CI enforcement unverified; no live-LLM e2e (deliberate) |

## 3. Feasibility spike & strategy

**Spike (this session, ~1 minute of commands, no Streamlit):**

| Probe | Package | UI |
| --- | --- | --- |
| Install from `uv.lock` `--frozen` | Yes | same venv |
| Native/build | `ty` + ruff pass | n/a |
| Boot | `[UNVERIFIED]` (launch banned) | same |
| ≥1 meaningful test | **33 passed** | no UI tests |

**Per component**

| Component | Strategy | Testability Milestone | Regime now | Safety rung | Residual risk |
| --- | --- | --- | --- | --- | --- |
| Package `debate_decision_system` | **A Freeze-then-lift** (already resurrected) | **Already crossed** (this checkout) | lit | **L3** | No characterization goldens of `advance()` transcripts; no live LLM |
| Streamlit UI | **Leave in place** | Unit-testable logic already in package. UI itself has **no** automated tests | lit for logic; UI dark for e2e | **L1** for pixels | Visual/session-state regressions undetected; do not add Playwright unless asked |
| SQLite memory | A | Already crossed (`tests/test_memory.py`) | lit | L3 | FTS/migrate paths partly covered |
| Compiled `debate_graph` | Leave / optional delete later | n/a | — | — | Drift vs `advance()` |

**CI Milestone:** **already stood up** in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (treat as Phase 0, complete). **Enforcing** required checks is a **human** GitHub Settings step. Agent cannot do it.

**Oracle:** source-as-spec + existing pytest. Self-frozen goldens only if a later phase adds `advance()` transcript snapshots. No production oracle on disk.

**Economic triage:** local alpha tool, no multi-tenant prod. Expensive rewrite unjustified.

## 4. Target architecture

**Keep the modular local monolith.** Same languages, same Streamlit, same SQLite.

| Piece | Action |
| --- | --- |
| Python 3.11–3.13, uv, Ruff, ty, pytest, prek | Keep |
| LangGraph + LangChain adapters | Keep |
| Streamlit multipage | Keep |
| SQLite + FTS | Keep |
| Keyword retrieve | Keep (swap to vectors only if keyword fails users) |
| `history.py` re-exports | Keep shim |
| Compiled `debate_graph` | Keep until a caller exists, or delete in a later XS if still unused |
| Live LLM e2e | **Dropped** (cost + flake). Not deferred. |
| Containers / auth / hosted API | **Dropped** unless product direction changes |

### ADR: Stay on current stack

- **Context:** Skill asked for a modernization target. Stack is already modern-python.
- **Decision:** Upgrade-in-place = no-op. Leave-in-place.
- **Alternatives:** Rewrite UI (React) — no capability gap. Swap LangGraph — stepper already custom. Postgres — one-user local file is enough.
- **Consequences:** Residual L3/L1 gaps stay until Phase 1–2 tests. No new deps.

### ADR: `advance()` is the contract

- **Context:** Two control planes (`StateGraph` vs `advance`).
- **Decision:** Seam tests pin `advance()` + `next_action`, not `debate_graph.invoke`.
- **Alternatives:** Switch UI to compiled graph — loses pause/inject.
- **Consequences:** `debate_graph` may rot. Phase 2 may delete it.

### ADR: No Streamlit e2e in this plan

- **Context:** Session rule + flake cost.
- **Decision:** Drop UI e2e. Package tests only.
- **Alternatives:** Playwright — deferred, not scheduled.
- **Consequences:** UI stays L1.

## 5. Per-feature migration analysis

| Feature | Now | Tactic | Testability | Rung | Effort | Risk | Accept |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Graph stepper | `graph.py` | Leave | already | L3 | XS | Routing drift | existing `test_debate` + optional goldens |
| Agents | `agents/` | Leave | already | L3 | S | LLM fail paths | keep fake clients |
| Tools / retrieve | `tools.py`, `retrieve.py` | Leave | already | L3 | S | web APIs die | unit tests; no live net in CI |
| Memory | `memory.py` | Leave | already | L3 | S | schema migrate | `test_memory` + migrate test |
| UI pages | `app_pages/` | Leave | n/a e2e | L1 | — | widget break | manual; out of plan |
| Analytics | `analytics.py` | Leave | already | L3 | XS | overlap false flags | existing tests |

All **Strategy A / Leave in place**. No beachhead rewrite.

## 6. Phased implementation plan

**Gating:** All scheduled phases are **lit** (package). Exit = runnable inventory commands. Do not advance without recording results. Trunk = **`main`**. No `master`. No stacked PRs.

**Phase 0 (CI + baseline): already complete** — workflow exists; this session: ruff, ty, pytest 33, audit clean.

### Phase 1: Safety net teeth (T-shirt: S)

**Goal:** Prove the existing net fails when `advance()` / memory contracts break.
**Regime:** lit — package
**Safety rung:** L3 (still no UI e2e)
**Prerequisites:** none
**Duration:** 1 short PR

#### Tasks

| ID | Task | Component | Blocked by |
| --- | --- | --- | --- |
| 1.1 | Add one `advance()` golden: fixed fake LLM, assert role sequence for open 2-seat 1-round | package | — |
| 1.2 | Mutate `should_judge` or `next_action` locally, confirm that test goes red, revert | package | 1.1 |
| 1.3 | Do not add hypothesis, Playwright, or new deps | — | — |

#### Risks & mitigations

- **Risk:** Golden too brittle to prompt text → **Mitigation:** assert roles + `debate_done`, not wording.

#### Decisions made

- Goldens pin **roles**, not judge prose. Dropped: live LLM tests. Deferred: UI e2e.

#### Hazards (Phase 2.5)

- H1 cleared — no dependency removal
- H2 cleared — no major bump
- H3 cleared — no runtime bump
- H4 cleared — no edge/auth
- H5 cleared — no store major
- H6 cleared — no insecure shim
- H7 — branch from `main`, merge before Phase 2
- H8 — if test command changes, update README + this file in same PR

#### Verification & Exit Criteria

- [ ] `uv run pytest` green
- [ ] `uv run ruff check` and `uv run ty check src/` green
- [ ] Net-proven-to-fail recorded (1.2) then reverted
- [ ] No behavior change outside tests
- [ ] Residual: UI still L1 — closed never in this plan (dropped)

### Phase 2: Coverage holes only (T-shirt: S)

**Goal:** Lift thin modules (`documents.py`, `llm.py` fail paths already partly tested) without new features.
**Regime:** lit
**Safety rung:** L3
**Prerequisites:** Phase 1 merged to `main`
**Duration:** 1 PR

#### Tasks

| ID | Task | Component | Blocked by |
| --- | --- | --- | --- |
| 2.1 | Tests for PDF/zip caps already in `test_tools`; add only if coverage on `documents.py` stays &lt; 70% after Phase 1 | package | 1 |
| 2.2 | Optional: delete `debate_graph` **only if** grep shows zero callers outside `graph.py` | package | 2.1 |
| 2.3 | Update `ARCHITECTURE.md` if 2.2 deletes | docs | 2.2 |

#### Decisions made

- No vector DB. No Postgres. Dropped: rewrite retrieve. Deferred: delete `debate_graph` until grep is clean.

#### Hazards

- H1 if 2.2 deletes symbol — grep all imports first
- H2–H6 cleared (no majors / auth / store / shims)
- H7 merge Phase 1 first
- H8 update architecture + README topology if graph helper removed

#### Verification & Exit Criteria

- [ ] `uv run pytest` coverage ≥ 80%
- [ ] `make lint`
- [ ] If delete `debate_graph`: grep empty + docs updated same PR

### Phase 3: Human CI enforcement (T-shirt: XS)

**Goal:** Make existing CI a required check.
**Regime:** lit
**Safety rung:** L3 → still L3 (enforcement is process)
**Prerequisites:** Phase 0 exists (already)
**Duration:** 5 minutes in GitHub UI

#### Tasks

| ID | Task | Component | Blocked by |
| --- | --- | --- | --- |
| 3.1 | Human: GitHub → Settings → Branches → require `quality` + `hooks` | platform | — |

#### Decisions made

- Agent does **not** invent a second workflow. Dropped: extra CI jobs.

#### Verification & Exit Criteria

- [ ] User confirms required checks on `main`
- [ ] Until then, treat green CI as convention only `[UNVERIFIED]`

**No further phases.** Future product work is not modernization.

## 7. Execution governance

- Branch `phase-1-advance-golden` then `phase-2-coverage` from **`main`**. Merge each before the next. `git log origin/main..HEAD` empty at cut.
- Lit exit = `make lint` + `uv run pytest`.
- Living plan: mark ✅ / ⏭️ / 🗑️ here when a phase ends.
- Topology change → update `ARCHITECTURE.md`, `README.md`, `.github/copilot-instructions.modernization.md` in the **same PR** (H8).
- Do not overwrite [`.github/copilot-instructions.md`](.github/copilot-instructions.md) (caveman). Sibling file holds commands.

## 8. Migration safety net

| Topic | Decision |
| --- | --- |
| Feature flags | None. No dual-run. |
| Data migration | Additive `_migrate` only. SQLite file is local/demo. Destructive reset of `data/decisions.db` is **allowed** for the operator; not a ship step. Prior file = backup. |
| Rollback | Revert the phase PR on `main`. |
| H6 register | Empty. No transitional insecure states. |
| Oracle | pytest + `advance()` role golden after Phase 1. |
| Testing | Stay on fake LLMs. Quarantine: live providers, Streamlit e2e. |
| Observability | None to match. `state["errors"]` is the seam. |

## 9. Open questions / stakeholder actions

1. **[DECISION NEEDED — human]** Enable branch protection / required status checks for `quality` and `hooks` on `main`.
2. Confirm Streamlit stay-unlaunched for agents (already in `AGENTS.md`).
3. Product direction (auth, hosted API, vectors): **out of scope** until you say otherwise.

No other blockers. Phases 1–2 are implementable without more answers.
