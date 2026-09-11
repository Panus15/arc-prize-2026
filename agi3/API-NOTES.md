# ARC-AGI-3 API — บันทึกจากของจริง

> ตรวจสอบเมื่อ 11 ก.ย. 2026 จาก package ที่ติดตั้งจริง: `arc-agi` 0.9.9 + `arcengine` 0.9.3
> ไม่ได้คัดลอกจากเอกสาร — ได้จากการ introspect ตัว type จริงด้วย Python

## Action space — 8 ค่า

```
RESET, ACTION1, ACTION2, ACTION3, ACTION4, ACTION5, ACTION6, ACTION7
```

`FrameData.available_actions: list[int]` บอกว่าเฟรมนั้น ๆ กดอะไรได้บ้าง — **ต้องเช็คทุกเฟรม**
ไม่ใช่สมมติว่ากดได้ครบ 8

## GameState — 4 ค่า

```
NOT_PLAYED, NOT_FINISHED, WIN, GAME_OVER
```

## FrameData

| field | type | หมายเหตุ |
|---|---|---|
| `game_id` | `str` | |
| `frame` | `list[list[list[int]]]` | **3 ชั้น** — เป็น stack ของ grid 2D ไม่ใช่ grid เดียว |
| `state` | `GameState` | |
| `levels_completed` | `int` | เดิมชื่อ `score` เปลี่ยนชื่อใน 0.9.3 (breaking change) |
| `win_levels` | `int` | |
| `action_input` | `ActionInput` | |
| `guid` | `str \| None` | |
| `full_reset` | `bool` | |
| `available_actions` | `list[int]` | |

## Agent interface

สืบทอดจาก `agents.agent.Agent` (ABC) แล้ว implement 2 เมธอด:

```python
def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool
def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction
```

ตัว base class จัดการ recording, tracing, และ `take_action` ให้แล้ว
**มี `Playback` agent มาให้ในตัว** — ไม่ต้องเขียนระบบ replay เอง ใช้ของ SDK ได้เลย

## สิ่งที่ต้องใช้ในการรันจริง

```bash
cp .env.example .env          # ใน ARC-AGI-3-Agents
# ARC_API_KEY="..."  ← จาก https://arcprize.org/platform
uv run main.py --agent=random --game=ls20
```

## ผลต่อการออกแบบ

- `frame` เป็น 3 ชั้น → ต้องรู้ว่าแต่ละชั้นคืออะไรก่อนเขียน perception layer
- `available_actions` เปลี่ยนได้ทุกเฟรม → policy ต้องอ่านค่านี้ ไม่ใช่ hard-code
- scoring ลงโทษ action เกินจำเป็นแบบกำลังสอง แต่ internal reasoning ฟรี
  → คุ้มที่จะคิดเยอะก่อนกด 1 ครั้ง มากกว่ากดลองหลายครั้ง
- `Playback` ที่มีอยู่แล้วทำให้ทดสอบ policy ซ้ำ ๆ ได้โดยไม่เปลืองโควตา API
