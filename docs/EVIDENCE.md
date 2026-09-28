# Evidence index

Every figure in the Paper Track writeup (`paper/writeup-draft.md`), the command
that reproduces it from this repository, and the document that recorded the
original run. The documents under `docs/` are the project's working notes and
are written in Thai; the commands and their output are not.

`python3 paper/trace_numbers.py` checks mechanically that every figure in the
writeup appears in one of those documents, and `./check.sh` runs that check with
the test suite, the lint, and the 1,500-word budget.

## Getting the recorded runs

Figures marked **R** replay the 500 recorded runs of the 25 public ARC-AGI-3
games (20 passes each) published by the Milestone #1 winner:

```bash
git clone --depth 1 https://github.com/Tufalabs/duck-harness.git
# every R command below takes:  --traces duck-harness/example-run/artifacts
```

Figures marked **M** come from environments we wrote and need nothing external.
Everything runs from `agi3/` after `./setup.sh`, as
`PYTHONPATH=. .venv/bin/python scripts/<script>`.

## Section 2 — Method

| Figure | Claim | Reproduce | Record |
|---|---|---|---|
| 8 of 25 | public games played almost entirely with MOUSE, never with a direction | **R** `completion_actions.py` (the games whose offers column has no `D`) | `prior-art-duck-harness.md`, `mode-switching.md` |

## Section 3 — Simulation does not predict reality

| Figure | Claim | Reproduce | Record |
|---|---|---|---|
| the table | four policies, quiet vs noise-calibrated mock | **M** `simulation_gap.py --skip-traces` | `simulation-gap.md` |
| 79%, 17 of 25 | control mapping recovered from real boards | **R** `simulation_gap.py` (component line) | `simulation-gap.md`, `real-game-validation.md` §3 |
| −0.93, 18 configurations | simulated vs real score correlation (not to be quoted as a correlation — see the writeup) | **R** `gap_correlation.py --games 12` | `gap-quantified.md` |

## Section 4 — Five failures

| # | Figures | Reproduce | Record |
|---|---|---|---|
| 1 | 95% of mock moves vs 0.4% (10 of 2,276) real; 1 game of 25; 1,255 real moves show anything moving, 1,741 show objects appearing | **M+R** `object_matching.py` | `real-game-validation.md` §2 (with dated corrections) |
| 2 | 91–100% of real clicks change the board; 1.0% clear a level; best colour 5.2× | **R** `click_signal.py` | `click-validation.md` |
| 3 | 3/3 quiet, 0/3 noisy | **M** `simulation_gap.py --skip-traces` | `simulation-gap.md` |
| 4 | overlap 55% vs centroid 79%; fallback 77% (22 of 24 points); all three on the noisy mock | **M+R** `estimator_comparison.py` | `estimator-comparison.md` §4b |
| 5 | ACTION5 on 97–100% of turns in 8 walking games (frozen walker) vs 0–10% (submitted) | **R** `replay_traces.py --walker v1` and `--walker current` | `static-actions.md` |
| ablation | which noise defeats the walker | **M** `pytest tests/test_noise.py`, or section 6 of `paper/notebook.ipynb` | `noise-validation.md` |

## Section 5 — What probing costs

| Figure | Claim | Reproduce | Record |
|---|---|---|---|
| 12 | median observations for a mapping correct about two directions | **R** `validate_control.py` | `control-learning-curve.md` |
| 56% / 72% / 81% at 10 / 40 / 80 | mapping accuracy against evidence | **R** `validate_control.py` | `control-learning-curve.md` |
| 0.6; 36%; 84–85% | confidence threshold and accuracy either side | **R** `validate_control.py` | `control-learning-curve.md` §3 |
| 12 → 10 | median cost with a balanced probe order | **R** `probe_order.py` | `probe-order.md` |

## Sections 6–8

| Figure | Claim | Reproduce | Record |
|---|---|---|---|
| 500 | recorded runs used for calibration | the traces above | `simulation-gap.md` §4 |
| test count | the suite size stated in section 7 | `.venv/bin/pytest` (`./check.sh` compares it with the writeup) | `ROADMAP.md` |
| 676; 22 | sb26: clicks that cleared nothing; completions, all by ACTION5 | **R** `click_signal.py`; `completion_actions.py` | `click-validation.md`, `mode-switching.md` |

## Pre-registration

Three agents were frozen before any real game file was obtained, with their git
commits and object hashes: `docs/PREREGISTRATION.md`. Results on real games will
be committed against those registrations, whatever they show.
