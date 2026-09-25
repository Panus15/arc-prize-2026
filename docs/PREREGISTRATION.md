# Pre-registration: the first run on real ARC-AGI-3 games

> ไฟล์นี้บันทึกว่า agent ถูก **ล็อกไว้ก่อน** เห็นเกมจริงเกมแรก เขียนเป็นอังกฤษเพราะเปเปอร์อ้างถึง
> commit ที่ล็อกไว้อยู่บน GitHub แล้วพร้อม timestamp — แก้ย้อนหลังไม่ได้

**Recorded:** 25 September 2026, before any real game file had been obtained.

## What is frozen

The agent in commit **`dc949b406a0cd6c82ad5cd8c55f835665e9e4109`** (`dc949b4`), public on
`github.com/Panus15/arc-prize-2026` since 25 Sep 2026 12:38 UTC.

| Path | Git object at that commit |
|---|---|
| `agi3/arcagi3/` (tree) | `883e84817101dddc0d7f27929912ccd4a799dc84` |
| `agi3/submission/my_agent.py` | `c4c1bc9a95bccd51d2c4ff8657ffbca547b0d3f8` |

Anyone can check these with `git rev-parse dc949b4:agi3/arcagi3` and
`git rev-parse dc949b4:agi3/submission/my_agent.py`.

## The prediction under test

Writeup §6: *"our own account predicts a further gap between the calibrated
environment and a live game."*

On the noise-calibrated mock (`docs/simulation-gap.md`, commit `4af7cf0`), seeded
random cleared **2/3** levels and our walking policy **0/3**. The real games are
different games, so absolute level counts do not carry over; **the ordering does.**

| Outcome on real walked games | Reading |
|---|---|
| our walker clears more levels than seeded random | **reversed** — the further gap §6 predicts |
| seeded random clears more | **held** — the mock carried over; counts against §6 |
| equal | **tied** — no evidence either way |

## Protocol

1. Obtain the public game files (`agi3/scripts/fetch_games.py`).
2. At commit `dc949b4`'s agent, run
   `python agi3/scripts/play_offline.py <games> --json-out paper/data/real-games-measured.json`
   with the default 400-action cap per game. Walked games are those the router
   sent to the navigator; clicked games are reported but do not enter the comparison.
3. Commit the result unedited, whatever it says.
4. Only after that, tune the agent against real games, in separate commits, and
   report tuned results as a separate, clearly labelled measurement.

## Addendum, same day: a second agent, also registered before any real game

After `dc949b4` was frozen, replaying the 500 recorded real runs through it showed
that in every walking game offering ACTION5 it pressed ACTION5 on 97-100% of turns
(`docs/static-actions.md`). That was found from recorded data, **still before any
real game file was obtained**. The fixed agent is registered here as a second,
separate measurement. Nothing about agent A or its protocol changes.

| | Agent A (as registered above) | Agent B |
|---|---|---|
| commit | `dc949b4` | **`fb5e2fb66ff1556608b3af82d74ec07e0c8b1271`** (25 Sep 2026 13:07 UTC) |
| `agi3/arcagi3/` tree | `883e848…` | `7a53d598b27913c9aed88331a3dbdd824b264ade` |
| `agi3/submission/my_agent.py` | `c4c1bc9…` | `bb12140f2a07cbf1d3e016784a315c95eefd3df9` |

Protocol for B is the same as for A, with A run first: both at the 400-action cap
against seeded random, both results committed unedited, and tuning on real games
only afterwards in separate commits. B's `MAX_ACTIONS` of 2,000 is the Kaggle
setting; the comparison uses 400 for both so they are measured alike.

What B changes, and what it does not claim: on recorded real boards its ACTION5
share is 0-10% and it made 0 errors in 500 passes; in six mock arenas it clears
every one. Whether it clears **real** levels is exactly what is not yet known.

## Addendum 2, same day: agent C, the one submitted to Kaggle

Also before any real game file. The recordings tag each level completion with
the action that caused it; in 4 of 25 public games that action is not the one
the action list suggests (`docs/mode-switching.md`). C adds two general rules
on top of B: switch between walking and clicking after 300 actions without a
level, in games offering both; and let the clicker press ACTION5 once per six
fruitless clicks where offered.

| | Agent C |
|---|---|
| commit | **`01562fc4dc97a5830038ff59970beba910518e51`** (2026-09-25T13:27:57+00:00) |
| `agi3/arcagi3/` tree | `989f4ee69b118e9412fe5f6ca2a310afe4d00fb2` |
| `agi3/submission/my_agent.py` | `bb12140f2a07cbf1d3e016784a315c95eefd3df9` (unchanged from B) |

C is run after A and B, under the same protocol. Because C can switch policy
mid-game, `play_offline.py` records for every game the policy it started with,
every policy it used, and how many levels each one cleared. The walker
comparison counts games by starting policy and counts only levels the walker
itself cleared.

## Why a file and not a git tag

A tag `prereg-real-games` was created on `dc949b4` but this development
environment refuses tag pushes. The commit itself is the public record; this file
names it.
