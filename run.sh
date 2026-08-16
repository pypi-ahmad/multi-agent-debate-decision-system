#!/usr/bin/env bash
# Native Linux launcher. Creates repo-root .venv with uv and runs the app inside it.
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Multi-Agent Debate Decision System ==="

if [[ ! -f pyproject.toml ]]; then
  echo "This folder is not the repo root. Clone the project, then run ./run.sh there."
  exit 1
fi
if [[ ! -f uv.lock ]]; then
  echo "uv.lock is missing. Re-clone https://github.com/pypi-ahmad/multi-agent-debate-decision-system"
  exit 1
fi
if [[ ! -f app.py ]]; then
  echo "app.py is missing. Re-clone the repository."
  exit 1
fi

export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  echo "uv not found. Installing with the official standalone installer..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    echo "Need curl or wget to install uv. See https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
  fi
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv installed but not on PATH. Open a new shell, or add \$HOME/.local/bin to PATH."
    exit 1
  fi
}

ensure_uv

ROOT="$(pwd)"
VENV="${ROOT}/.venv"
export UV_PROJECT_ENVIRONMENT="${VENV}"

if [[ ! -x "${VENV}/bin/python" ]]; then
  echo "First-time setup: creating project-root .venv with uv..."
  uv python install
  uv venv "${VENV}" --allow-existing
fi

if [[ ! -x "${VENV}/bin/streamlit" ]]; then
  echo "Installing project dependencies into .venv..."
  uv sync --project "${ROOT}"
  if [[ ! -x "${VENV}/bin/streamlit" ]]; then
    echo "Setup finished but Streamlit is still missing from .venv."
    exit 1
  fi
  echo "First-time setup done. Environment: ${VENV}"
else
  echo "Using existing project venv: ${VENV}"
fi

if [[ ! -f .env && -f .env.example ]]; then
  echo "No .env found - copying .env.example as a starting point."
  cp .env.example .env
  echo "Edit .env with API keys if you are not using Ollama only. OS env vars still win."
fi

mkdir -p data/debates data/lancedb

echo "Activating .venv and starting http://localhost:8522 ..."
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
exec streamlit run app.py
