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

## Why a file and not a git tag

A tag `prereg-real-games` was created on `dc949b4` but this development
environment refuses tag pushes. The commit itself is the public record; this file
names it.
