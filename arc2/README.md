# ARC-AGI-2 workspace

A self-contained workspace for working with the **ARC-AGI-2** public corpus:
a reproducible fetch of the dataset, a validating loader, terminal rendering,
and tests.

## What the dataset repo is (and isn't)

[`arcprize/ARC-AGI-2`](https://github.com/arcprize/ARC-AGI-2) is **data only** —
1,000 public training tasks and 120 public evaluation tasks as JSON, plus a
readme and an Apache-2.0 licence. It ships **no `requirements.txt` and no Python
code**, so there is nothing to `pip install -r` from that clone. The
`requirements.txt` here is this workspace's own.

The dataset is treated as an external checkout, not vendored source: `setup`
clones it to `ARC-AGI-2/` and `.gitignore` keeps it out of version control.

## Setup

```bash
./setup.sh          # macOS / Linux
```

```bat
setup.bat           REM Windows
```

Either script clones the dataset (shallow), creates `.venv`, installs
`requirements.txt`, and verifies that all 1,120 tasks parse. Both are safe to
re-run — an existing checkout is pulled, an existing venv reused.

Doing it by hand is the same three steps:

```bash
git clone --depth 1 https://github.com/arcprize/ARC-AGI-2.git
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # .venv\Scripts\pip on Windows
```

Requires Python 3.11+ and `git` on `PATH`.

## Usage

```bash
source .venv/bin/activate     # .venv\Scripts\activate on Windows

python -m arc verify          # validate every task against the grid spec
python -m arc stats           # grid-size and pair-count summary per split
python -m arc show 007bbfb7   # render a task in the terminal (colour if supported)
python -m arc show 00576224 --split evaluation --no-color
pytest                        # schema tests + a full pass over the corpus
```

In code:

```python
from arc import load_task, iter_split, task_ids

task = load_task("007bbfb7")            # split defaults to "training"
print(len(task.train), len(task.test))
print(task.train[0].input_shape)        # (rows, cols)

for task in iter_split("evaluation"):   # streams; does not hold 120 tasks in memory
    ...

ids = task_ids("training")              # 1000 sorted ids
```

`load_task` / `parse_task` validate as they load and raise `TaskFormatError` on
anything off-spec: ragged grids, symbols outside 0–9, dimensions outside
1×1–30×30, booleans posing as ints, or missing `train`/`test` sections. Test
outputs are allowed to be absent so held-out formats parse; `arc verify` asserts
they are present in the public splits, since a missing one there means a
truncated checkout.

## Layout

```
arc2/
├── arc/
│   ├── dataset.py     loading + schema validation
│   ├── render.py      ANSI grid rendering (zero dependencies)
│   └── __main__.py    the `python -m arc` CLI
├── tests/             schema tests (no checkout needed) + corpus tests
├── requirements.txt
├── setup.sh · setup.bat
└── ARC-AGI-2/         dataset checkout — created by setup, gitignored
```

## Pointing at a different copy of the data

Set `ARC_AGI_2_DATA` to any directory containing `training/` and `evaluation/`:

```bash
ARC_AGI_2_DATA=/data/arc-agi-2/data python -m arc verify
```

## Task format

Each JSON file is `{"train": [pair, ...], "test": [pair, ...]}` where a pair is
`{"input": grid, "output": grid}` and a grid is a rectangular list of rows of
integers 0–9, between 1×1 and 30×30. A task counts as solved only when every
test output matches exactly, including its dimensions — 2 attempts per test
input. See the [dataset readme](https://github.com/arcprize/ARC-AGI-2) and
[On the Measure of Intelligence](https://arxiv.org/abs/1911.01547).

The corpus is Apache-2.0 licensed by the ARC Prize Foundation; this workspace
only fetches it.
