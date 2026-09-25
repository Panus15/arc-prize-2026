#!/usr/bin/env bash
# Fetch the official ARC-AGI-3 runner into agi3/vendor/ and slim it.
#
# The runner's agents/__init__.py imports every LLM template it ships
# (langgraph, smolagents, openai, ...). We need none of them, so it is replaced
# with the same minimal version the official Kaggle sample writes at run time.
# Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

DEST=vendor/ARC-AGI-3-Agents
if [ -d "$DEST/.git" ]; then
    git -C "$DEST" pull --ff-only --quiet
else
    mkdir -p vendor
    git clone --depth 1 --quiet https://github.com/arcprize/ARC-AGI-3-Agents.git "$DEST"
fi

cat > "$DEST/agents/__init__.py" <<'PY'
"""Slimmed by agi3/scripts/vendor_framework.sh — only what our agent needs."""
from typing import Type

from dotenv import load_dotenv

from .agent import Agent, Playback
from .swarm import Swarm
from .templates.random_agent import Random

load_dotenv()

AVAILABLE_AGENTS: dict[str, Type[Agent]] = {"random": Random}
PY

echo "runner ready at agi3/$DEST ($(git -C "$DEST" rev-parse --short HEAD))"
