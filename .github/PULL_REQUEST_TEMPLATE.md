## What this does

A short description of the change — what was added, fixed, or improved.

## Why

Link to the issue or explain why this matters if there is no issue. For obvious fixes, one sentence is fine.

## Type

- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] Test coverage
- [ ] Refactor / code quality
- [ ] New persona
- [ ] RAG improvement
- [ ] Other

## Checklist

- [ ] `make lint` passes (`ruff format --check`, `ruff check`, `ty check src/`)
- [ ] `make test` passes (coverage ≥ 80%)
- [ ] Tests use fake chat clients — no live LLM calls added
- [ ] No new unrestricted `exec` / `eval` / shell execution
- [ ] No API keys or secrets committed
- [ ] No donation, sponsorship, or payment features added
- [ ] Docs updated if behavior changed (`docs/how-to-use.md`, `docs/technical.md`)

## Testing notes

How you verified the change works — manual run, new test, or both.

## Breaking changes

Any API or behavior change that could affect an existing setup. Leave blank if none.

---

> [!NOTE]
> This project runs locally on the reviewer's machine. If you added a new provider, model, or env var, make sure it appears in [docs/technical.md](../docs/technical.md) and [CONTRIBUTING.md](../CONTRIBUTING.md).
>
> All data processed by this app is 100% the user's responsibility — see [DISCLAIMER.md](../DISCLAIMER.md).
