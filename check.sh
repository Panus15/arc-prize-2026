#!/usr/bin/env bash
# Everything that must hold before a commit, in one command. Stops at the first
# failure: no step's exit status is lost in a pipe (one was, once).
#
#     ./check.sh
set -euo pipefail
cd "$(dirname "$0")"

PY=agi3/.venv/bin/python
step() { printf '\n== %s\n' "$1"; }

step "lint"
ruff check --config agi3/ruff.toml agi3/ paper/

step "tests"
out=$(cd agi3 && PYTHONPATH=. ../"$PY" -m pytest 2>&1) || { echo "$out" | tail -30; exit 1; }
echo "$out" | tail -1
passed=$(echo "$out" | sed -n 's/^\([0-9]*\) passed.*/\1/p' | tail -1)
claimed=$(tr '\n' ' ' < paper/writeup-draft.md | grep -o '[0-9][0-9]* tests cover' | grep -o '^[0-9]*' || true)
if [ -n "$claimed" ] && [ "$claimed" != "$passed" ]; then
    echo "the writeup says $claimed tests; the suite has $passed"; exit 1
fi

step "writeup word budget (limit 1,500, 70 reserved)"
python3 paper/wordcount.py

step "every figure in the writeup appears in a measurement document"
python3 paper/trace_numbers.py

step "no API key in any tracked file"
key=$(sed -n 's/^ARC_API_KEY=//p' agi3/.env 2>/dev/null || true)
if [ -n "$key" ] && git grep -q -F -- "$key"; then
    echo "the API key appears in a tracked file"; exit 1
fi
echo "clean"

printf '\nall checks passed\n'
