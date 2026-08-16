## What

A few sentences. Link the issue if there is one.

## Why

## How to check

- [ ] `uv run ruff check` and `uv run ruff format --check`
- [ ] `uv run ty check src/`
- [ ] `uv run pytest` (coverage ≥ 80%)
- [ ] No `.env`, `data/decisions.db`, or `data/lancedb/` in the diff
- [ ] Provider model lists and env-only keys unchanged (unless the issue is about them)
- [ ] I did not add donation, sponsorship, or payment machinery

## Notes

Anything a reviewer should not miss.

By opening this PR you agree the change stays MIT-licensed and that testers run it on their own machines with their own keys. See [DISCLAIMER.md](DISCLAIMER.md).
