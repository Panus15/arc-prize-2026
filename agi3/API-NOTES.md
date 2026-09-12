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

---

## เพิ่มเติม: กับดักที่เจอตอนเขียนโค้ดจริง (11 ก.ย. 2026)

### 1. `GameAction(int)` ใช้ไม่ได้ — และนี่คือกับดักที่ทำให้โค้ดพังเงียบ ๆ

`FrameData.available_actions` คืนค่าเป็น `list[int]` แต่ **สร้าง `GameAction` จาก int ตรง ๆ ไม่ได้**

```python
GameAction(1)   # ValueError: 1 is not a valid GameAction
```

เพราะ `_value2member_map_` ใช้คีย์เป็น **tuple `(value, action_class)`**:

```
{(0, SimpleAction): GameAction.RESET, (1, SimpleAction): GameAction.ACTION1, ...
 (6, ComplexAction): GameAction.ACTION6, ...}
```

ทางแก้อยู่ที่ `arcagi3/actions.py` → `action_from_value()` / `actions_from_values()`
มีเทสคุมไว้ว่าถ้า SDK รุ่นใหม่แก้เรื่องนี้ เทสจะ fail เพื่อให้ถอด workaround ออกได้

### 2. ACTION6 เป็น `ComplexAction` ตัวเดียวในชุด

อีก 7 ตัว (RESET, ACTION1-5, ACTION7) เป็น `SimpleAction`
→ ACTION6 ต้องส่ง payload ใน `ActionInput.data` (น่าจะเป็นพิกัด click)
**เลือกแค่ตัว enum เฉย ๆ ไม่พอ** ยังไม่ได้ยืนยันรูปแบบ data เพราะยังไม่ได้ต่อ API จริง

### 3. `ActionInput` มีฟิลด์ `reasoning`

```python
ActionInput(id=GameAction.ACTION1, data={}, reasoning=...)
```

สอดคล้องกับที่กติกาบอกว่า **internal reasoning ไม่ถูกนับเป็นต้นทุน แต่ action ถูกนับ**

### 4. `EnvironmentScore` ยืนยันว่าคะแนนวัดประสิทธิภาพ ไม่ใช่แค่จบเกม

ฟิลด์ที่มีจริง: `level_actions`, `level_baseline_actions`, `level_scores`,
`actions`, `resets`, `levels_completed`

→ **มี baseline ต่อ level ให้เทียบ** การจบเกมอย่างเดียวไม่พอ ต้องจบด้วยจำนวน action ที่ใกล้ baseline

### 5. SDK รันเกมในเครื่องได้ — ไม่ต้องใช้ API key ตอนพัฒนา

`arc_agi.local_wrapper.LocalEnvironmentWrapper` + `arcengine.base_game.ARCBaseGame`
→ เขียนเกมเองแล้วรันผ่าน wrapper ตัวเดียวกับที่ใช้ตอนแข่งได้
