#!/usr/bin/env bash
# First-time setup for the ARC-AGI-2 workspace (macOS / Linux).
#   1. fetch the dataset repo as a shallow external checkout
#   2. create .venv and install requirements.txt
#   3. verify all 1120 public tasks parse
# Safe to re-run: an existing checkout is updated, an existing venv is reused.
set -euo pipefail

cd "$(dirname "$0")"

DATASET_URL="https://github.com/arcprize/ARC-AGI-2.git"
DATASET_DIR="ARC-AGI-2"
PYTHON="${PYTHON:-python3}"

echo "==> Dataset"
if [ -d "$DATASET_DIR/.git" ]; then
    echo "    $DATASET_DIR already present — pulling latest"
    git -C "$DATASET_DIR" pull --ff-only --depth 1 origin HEAD
else
    git clone --depth 1 "$DATASET_URL" "$DATASET_DIR"
fi

echo "==> Virtual environment"
if [ ! -d .venv ]; then
    "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt

echo "==> Verifying dataset"
.venv/bin/python -m arc verify

cat <<'DONE'

Setup complete. Activate the environment with:

    source .venv/bin/activate

Then try:

    python -m arc stats
    python -m arc show 007bbfb7
    pytest
DONE
