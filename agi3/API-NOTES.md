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
| `frame` | `list[list[list[int]]]` | **stack ของ grid 2D** — ดูข้อ 6 ด้านล่าง อ่านเลเยอร์**สุดท้าย** ไม่ใช่ index 0 |
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

- `frame` เป็น stack → ต้องอ่านเลเยอร์สุดท้าย (ดูข้อ 6)
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

---

## ยืนยัน: ความหมายของแต่ละ action (13 ก.ย. 2026)

จาก `inference/agent/action_names.py` ของโซลูชันที่ชนะ Milestone #1:

| engine | ความหมายในเกม |
|---|---|
| `ACTION1` | UP |
| `ACTION2` | DOWN |
| `ACTION3` | LEFT |
| `ACTION4` | RIGHT |
| `ACTION5` | SPACE |
| `ACTION6` | MOUSE — ส่ง `row`, `col` |
| `RESET` | RESET |

**`ACTION7` ไม่ถูก map ไว้** — ยังไม่รู้ว่าใช้ทำอะไร

รูปแบบการสั่ง: `action(['LEFT'])` หรือ `action([{'action':'MOUSE','row':4,'col':7}])`

## Perception ที่ผู้ชนะใช้ (สำคัญ)

prompt ของเขาบอกชัดว่า **ไม่ให้โมเดลเห็น grid ตัวเลขดิบเลย** ("The raw numeric grid is
intentionally not exposed") แต่ให้ **segmentation** แทน:

- node = วัตถุสี่เชื่อม (4-connected) สีเดียวกัน · เรียง id จากบนลงล่าง ซ้ายไปขวา
- แต่ละ node มี: `color`, `pixels`, `boundary`, `children` (วัตถุที่ถูกล้อมอยู่ข้างใน),
  และ **`hash` = ลายเซ็นรูปร่าง+สีที่ไม่ขึ้นกับตำแหน่ง** → ใช้ติดตามวัตถุข้ามเฟรม
- `adjacency_list` = คู่ node ที่ติดกัน

เราสร้างชั้นนี้ไว้แล้วที่ `arcagi3/perception.py`

### กับดักที่ผู้ชนะเตือนไว้เอง

> แถบยาวติดขอบจอมักเป็น **timer/HUD ไม่ใช่ชิ้นส่วนปริศนา**
> ความผิดพลาดที่พบบ่อยคือไปไล่คลิกทีละช่องบนแถบนั้น

- board จริงคือ **64×64**
- `WIN` = จบทั้งเกม ส่วนการผ่าน level กลางทางจะเห็นเป็น **คะแนนเพิ่มขึ้นแต่เกมยังเล่นต่อ**
- **อย่าสมมติว่ามีตัวละครให้บังคับ** บางเกมไม่มี player avatar เลย

### 6. 🔴 `frame` คือ "ภาพเคลื่อนไหว" ไม่ใช่ "เลเยอร์" — อ่านตัวสุดท้าย

ตรวจจาก source ของ `arcengine.base_game.ARCBaseGame.perform_action`:

```python
while not self.is_action_complete():
    ...
    frame = self.camera.render(self.current_level.get_sprites())
    frame_list.append(frame.tolist())
```

**engine วาดภาพหนึ่งครั้งต่อ 1 step ของ action ที่ยังทำงานไม่จบ แล้วต่อท้ายเข้า list**
ดังนั้น:

- `frame[0]` = ภาพ**ระหว่างทาง** ของ action ที่ยังไม่นิ่ง
- **`frame[-1]` = กระดานที่นิ่งแล้ว ซึ่งเป็นตัวที่ action ถัดไปจะกระทำต่อ**

> ⚠️ **แก้สมมติฐานเดิม** — บันทึกฉบับแรกเขียนว่า "อ่าน index 0" ซึ่ง**ผิด**
> `sdk_adapter.normalise_frame()` ยุบ stack ให้เหลือกระดานที่นิ่งแล้วก่อนส่งให้ policy
> ทำให้ policy ที่เขียนไว้เดิม (ซึ่งอ่าน `frame[0]`) ยังทำงานถูกต้องโดยไม่ต้องแก้

ข้อนี้อ่านจาก engine ที่รันในเครื่อง — **ยังไม่ได้ยืนยันกับ server จริง**

### 7. ACTION6 ส่ง payload ผ่าน `set_data` บนตัว enum

```python
action = GameAction.ACTION6
action.set_data({"x": col, "y": row})   # x = คอลัมน์, y = แถว
```

`get_pixels` ใน engine slice แบบ `frame[y:y+h, x:x+w]` → **y คือแถว, x คือคอลัมน์**
payload ติดอยู่กับ enum member ที่ใช้ร่วมกันทั้ง process ซึ่งเป็นสัญญาของ SDK เอง
(`do_action_request` อ่าน `action.action_data` จาก member ที่ agent คืนมา)

### 8. `frame=[]` เป็นสถานะปกติ

engine คืน `frame=[]` ตอน WIN และ GAME_OVER และ SDK ใส่ `FrameData` เปล่าไว้เป็นเฟรมแรก
→ **"ไม่มีกระดาน" ไม่ใช่ข้อมูลเสีย** ต้องรองรับ ไม่ใช่ crash
