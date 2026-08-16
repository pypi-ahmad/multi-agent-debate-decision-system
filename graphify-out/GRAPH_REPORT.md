# Graph Report - Multi-Agent Debate  Decision System  (2026-08-16)

## Corpus Check
- Corpus is ~27,111 words - fits in a single context window. You may not need a graph.

## Summary
- 399 nodes · 1152 edges · 19 communities (15 shown, 4 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 129 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- RAG embeddings pipeline
- Debate agent nodes
- SQLite decision memory
- Docs CI community
- Provider env config
- Streamlit debate pages
- Grounded tools retrieve
- Analytics quality report
- Package CLI identity
- Judge test fakes
- Linux run.sh launcher
- Local-only providers
- RAG test isolation
- OpenCode caveman rule
- Windsurf caveman rule
- Package name

## God Nodes (most connected - your core abstractions)
1. `DebateState` - 64 edges
2. `initial_state()` - 33 edges
3. `get_chat_model()` - 23 edges
4. `save_debate()` - 23 edges
5. `knowledge_block()` - 18 edges
6. `DebaterSpec` - 18 edges
7. `search_decisions()` - 17 edges
8. `Chunk` - 17 edges
9. `Multi-Agent Debate Decision System` - 17 edges
10. `run_rag()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Not Here Constraints` --semantically_similar_to--> `Feature Out of Scope`  [INFERRED] [semantically similar]
  docs/technical.md → .github/ISSUE_TEMPLATE/feature_request.md
- `LanceDB Hybrid RAG` --semantically_similar_to--> `Keyword Retrieve`  [INFERRED] [semantically similar]
  README.md → ARCHITECTURE.md
- `_sync()` --uses--> `DebateState`  [INFERRED]
  app_pages/debate.py → src/debate_decision_system/state.py
- `_render_turn()` --uses--> `Turn`  [INFERRED]
  app_pages/debate.py → src/debate_decision_system/state.py
- `Auto-Clarity` --conceptually_related_to--> `Private Security Advisory`  [INFERRED]
  .clinerules/caveman.md → SECURITY.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Lint Test Audit Hook Gates** — _github_workflows_ci_quality_job, _github_workflows_ci_hooks_job, _pre_commit_config_prek_hooks, _github_pull_request_template_pr_checklist, docs_technical_quality_gates [INFERRED 0.85]
- **Caveman Agent Instruction Policy** — _clinerules_caveman_caveman_tone, _github_copilot_instructions_caveman_tone, _opencode_agents_caveman_tone, _windsurf_rules_caveman_caveman_tone, agents_caveman_tone [EXTRACTED 1.00]
- **Stepped Hearing Control Flow** — architecture_advance_stepper, architecture_team_huddle, architecture_grounded_mode, architecture_judge_structured_output, readme_decision_report [INFERRED 0.85]

## Communities (19 total, 4 thin omitted)

### Community 0 - "RAG embeddings pipeline"
Cohesion: 0.08
Nodes (60): embed_text(), _EmbedState, hashed_embed(), _l2(), _ollama_embed(), _ollama_embed_legacy(), Deterministic bag-of-tokens embedding. No network. Tests and offline., Return (vector, backend). Prefer Ollama; fall back to hashed. (+52 more)

### Community 1 - "Debate agent nodes"
Cohesion: 0.11
Nodes (56): BaseMessage, current_debater(), debater_node(), huddle_node(), judge_node(), max_speeches(), moderator_node(), next_speaker_index() (+48 more)

### Community 2 - "SQLite decision memory"
Cohesion: 0.11
Nodes (53): Connection, Row, initial_state(), _normalize_seat(), _agent_models(), archive_decision(), _as_bool(), _col() (+45 more)

### Community 3 - "Docs CI community"
Cohesion: 0.07
Nodes (48): Auto-Clarity, Caveman Tone, Copilot Caveman Tone, Manual CI Enforcement, Copilot Modernization Instructions, Phase Gating, Dependabot Weekly Updates, Bug Report Template (+40 more)

### Community 4 - "Provider env config"
Cohesion: 0.08
Nodes (39): agnes_api_key(), agnes_base_url(), env(), google_api_key(), key_present(), list_ollama_models(), models_for_provider(), ollama_base_url() (+31 more)

### Community 5 - "Streamlit debate pages"
Cohesion: 0.14
Nodes (20): _model_options(), _ollama_models(), _pick_provider_model(), _read_uploads(), _render_turn(), _sync(), _save_uploads(), cache_data (+12 more)

### Community 6 - "Grounded tools retrieve"
Cohesion: 0.17
Nodes (23): AST, retrieve(), allowed_tools(), calculator(), _eval_code(), _eval_num(), execute_tool(), _get_json() (+15 more)

### Community 7 - "Analytics quality report"
Cohesion: 0.20
Nodes (17): circular_pairs(), mean_strength(), participation(), participation_balance(), persona_win_rates(), Any, quality_report(), Mean argument strength by date (YYYY-MM-DD). (+9 more)

### Community 8 - "Package CLI identity"
Cohesion: 0.27
Nodes (6): main(), Return the CLI identity string., Print the package identity and exit., version_banner(), test_main_prints_banner(), test_version_banner_includes_name_and_version()

### Community 9 - "Judge test fakes"
Cohesion: 0.25
Nodes (6): JudgeOutput, BaseModel, SpeechScoreModel, _FakeChat, _FakeJudge, test_nodes_with_fake_llm()

### Community 10 - "Linux run.sh launcher"
Cohesion: 0.50
Nodes (4): ensure_uv(), PATH, run.sh script, UV_PROJECT_ENVIRONMENT

### Community 11 - "Local-only providers"
Cohesion: 0.50
Nodes (4): local_only Seat Rewrite, Locked Provider Model Lists, Fully Local Mode, LLM Providers

## Knowledge Gaps
- **15 isolated node(s):** `debate-decision-system`, `PATH`, `UV_PROJECT_ENVIRONMENT`, `_EmbedState`, `Caveman Tone` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DebateState` connect `Debate agent nodes` to `RAG embeddings pipeline`, `SQLite decision memory`, `Streamlit debate pages`, `Grounded tools retrieve`, `Analytics quality report`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Why does `initial_state()` connect `SQLite decision memory` to `RAG embeddings pipeline`, `Debate agent nodes`, `Provider env config`, `Streamlit debate pages`, `Grounded tools retrieve`, `Analytics quality report`, `Judge test fakes`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `get_chat_model()` connect `Provider env config` to `Debate agent nodes`, `Grounded tools retrieve`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 49 inferred relationships involving `DebateState` (e.g. with `_sync()` and `current_debater()`) actually correct?**
  _`DebateState` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `initial_state()` (e.g. with `DebaterSpec` and `DebateState`) actually correct?**
  _`initial_state()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `save_debate()` (e.g. with `DebateState` and `test_phase3_local_retrieve_history()`) actually correct?**
  _`save_debate()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `debate-decision-system`, `PATH`, `UV_PROJECT_ENVIRONMENT` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._