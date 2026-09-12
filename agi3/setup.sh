#!/usr/bin/env bash
# Set up the ARC-AGI-3 workspace. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

# The competition SDK pins Python 3.12; 3.11 cannot resolve arc-agi.
PYTHON="${PYTHON:-python3.12}"
if ! command -v "$PYTHON" >/dev/null; then
    echo "[ERROR] $PYTHON not found. ARC-AGI-3 requires Python 3.12." >&2
    exit 1
fi

[ -d .venv ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt

echo
echo "Setup complete. Try:"
echo "    .venv/bin/pytest"
echo "    .venv/bin/python -m arcagi3 play --agent random"
