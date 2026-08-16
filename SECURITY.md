# Security

Thank you for helping keep this project safe. Reports from the community are welcome and appreciated.

## This is a local app

The Streamlit UI, SQLite file (`data/decisions.db`), and LanceDB store (`data/lancedb/`) run on **your** machine. There is no hosted multi-user service and no project-operated API. You supply every credential (OS environment or `.env`). Anything you upload or debate is **your** responsibility — see [DISCLAIMER.md](DISCLAIMER.md).

## Supported versions

Only `main` is maintained.

## What to report

Please report privately:

- Secret leakage (keys written to git, logs, or exports)
- Unsafe code execution beyond the restricted `ast` calculator / math eval
- Path traversal or unexpected file reads on upload / zip extract
- Prompt or tool behavior that can exfiltrate local files without the user asking

Do **not** report: model quality, “the judge was wrong,” or missing features. Use a [bug](.github/ISSUE_TEMPLATE/bug_report.md) or [feature](.github/ISSUE_TEMPLATE/feature_request.md) issue for those.

Do **not** open a public issue that includes live API keys or confidential documents.

## How to report

Use GitHub **Security Advisories** on this repository (private report):

https://github.com/pypi-ahmad/multi-agent-debate-decision-system/security/advisories/new

Include:

1. What you did
2. What happened
3. Impact
4. A minimal reproduction if you have one

You will hear back when the report has been triaged. Please give a reasonable window before any public write-up.

## Hard rules in this repo

- Never commit `.env`, `.streamlit/secrets.toml`, or local databases
- Do not add unrestricted `exec` / `eval` / shell tools
- Do not weaken the grounded-mode tool allow-list without a design discussion

There is no bug bounty and no payment for reports. Please do not offer or request money.
