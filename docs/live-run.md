# วิธีรันเกมจริง — ทำบนเครื่องคุณ

> **ทำไมต้องเป็นคุณ:** container ที่ผมทำงานอยู่ถูก egress proxy บล็อก `arcprize.org`
> (`CONNECT tunnel failed, response 403`) และผมจะไม่หลบนโยบายนั้น
> **งานทั้งหมดในไฟล์นี้ใช้เวลาไม่เกินครึ่งชั่วโมง และปลดล็อกงานที่เหลือทุกข้อ**

## 0. ทำไมข้อนี้สำคัญที่สุด

| ปลดล็อกอะไร | ทำไม |
|---|---|
| **Accuracy** ในเกณฑ์ให้คะแนน | 1 ใน 6 ข้อที่ถ่วงน้ำหนักเท่ากัน · ต่ำกว่า 3 = ค่าเฉลี่ยไม่ถึง 4.5 |
| **§1 ปิดท้าย** ของเปเปอร์ | ตอนนี้ปิดด้วยคำสัญญา ควรปิดด้วยตัวเลขจริง |
| **§8 ช่องว่างชั้นที่ 5** | เปเปอร์**ทำนายไว้แล้ว** ว่าจะเจอ — ข้อนี้ทำให้เปลี่ยนจาก "สังเกตย้อนหลัง" เป็น "ทำนายแล้วตรวจ" |

ข้อสุดท้ายคือจุดที่ทำให้เปเปอร์แข็งที่สุด **และเราจะชนะหรือแพ้คำทำนายก็ได้ทั้งคู่**
ถ้าทำนายผิดก็เขียนว่าผิด — นั่นก็ยังเป็นผลการทดลองที่ซื่อสัตย์

## 1. เตรียมเครื่อง (ครั้งเดียว)

ต้องมี **Python 3.12** (SDK บังคับ — 3.11 resolve `arc-agi` ไม่ผ่าน)

```bash
git clone https://github.com/Panus15/arc-prize-2026.git
cd arc-prize-2026/agi3
./setup.sh                     # Windows: ดู setup.bat
.venv/bin/pytest -q            # ควรผ่านทั้งหมด
```

ใส่ API key — **สร้างไฟล์เอง อย่าเอา key ไปวางในแชตหรือใน commit**

```bash
printf 'ARC_API_KEY=%s\n' 'คีย์ของคุณ' > .env
chmod 600 .env                 # .env อยู่ใน .gitignore อยู่แล้ว
```

## 2. เช็คการเชื่อมต่อ — ยังไม่กิน scorecard

```bash
.venv/bin/python scripts/check_live.py
```

สคริปต์นี้ **read-only** และ**พิมพ์แค่ความยาวของ key ไม่พิมพ์ตัว key**
ผลที่ควรได้:

```
key loaded (36 characters)
connection OK — N games reachable
  ls20
  ...
```

| ถ้าเจอ | แปลว่า | ทำอะไรต่อ |
|---|---|---|
| `connection OK` | ใช้ได้ | ไปข้อ 3 |
| `the server rejected the key (401)` | key ผิดหรือหมดอายุ | ออก key ใหม่จากหน้าเว็บ |
| `could not reach ...` | เน็ต/firewall | ลองเน็ตอื่น |

**ส่งผลข้อนี้กลับมาให้ผมได้เลย** (ไม่มี key อยู่ในนั้น) — แค่นี้ผมก็เริ่มเขียนต่อได้

## 3. รันเกมจริงด้วย policy ของเรา

ตัว runner เป็นของ ARC Prize ไม่ได้ vendor ไว้ใน repo นี้ ต้อง clone แยก

```bash
git clone https://github.com/arcprize/ARC-AGI-3-Agents.git
cd ARC-AGI-3-Agents
```

สร้างไฟล์ `agents/templates/arcagi3_navigator.py`:

```python
from arcagi3.navigator import NavigatorAgent
from arcagi3.sdk_adapter import SDKPolicyAdapter

from ..agent import Agent


class Navigator(SDKPolicyAdapter, Agent):
    """Our policy, driven by the official runner."""

    MAX_ACTIONS = 200
    policy_factory = NavigatorAgent
```

แล้ว `import` คลาสนี้ใน `agents/__init__.py` (`AVAILABLE_AGENTS` สร้างจาก
`Agent.__subclasses__()` — แค่ import ก็ลงทะเบียนให้อัตโนมัติ) จากนั้น:

```bash
export ARC_API_KEY=...          # หรือให้มันอ่านจาก .env ตามวิธีของ runner
export RECORDINGS_DIR=./recordings
PYTHONPATH=/path/to/arc-prize-2026/agi3 uv run main.py --agent=navigator --game=ls20
```

> ⚠️ **ทุก action กินโควตา scorecard** เริ่มจาก **เกมเดียวก่อน** ดูว่าไม่พัง
> ค่อยรันเกมอื่น อย่ารันรวดทุกเกมในครั้งแรก

**ลำดับ mixin สำคัญ:** `SDKPolicyAdapter` ต้องมาก่อน `Agent` ไม่งั้น ABC ไม่ครบ

## 4. สรุปผลให้เป็นตัวเลข

```bash
cd /path/to/arc-prize-2026/agi3
.venv/bin/python scripts/summarise_live.py /path/to/ARC-AGI-3-Agents/recordings \
    --json-out live.json
```

จะได้หน้าตาแบบนี้:

```
1 game(s)

  ls20       lost 0/3 levels in 200 actions

games won      0/1
levels cleared 0
actions spent  200

prediction on record: 0 levels (our policies clear 0/3 on the noisy mock)
outcome: prediction held — the live game is at least as hard as the mock
```

**ส่ง `live.json` กลับมา** ไฟล์เล็ก ไม่มี key ไม่มีข้อมูลส่วนตัว
ผมจะเอาไปเติม §1 กับ §8 และ commit เข้า `paper/data/` เป็นหลักฐาน

## 5. สิ่งที่ผมต้องการกลับมา — สรุปสั้น ๆ

| ลำดับ | สิ่งที่ส่ง | ได้จาก | ปลดล็อก |
|---|---|---|---|
| 1 | ผล `check_live.py` (คัดลอกข้อความ) | ข้อ 2 | ยืนยันว่าเชื่อมได้จริง |
| 2 | `live.json` | ข้อ 4 | §1 · §8 · Accuracy |
| 3 | เลข score ที่ Kaggle แสดงหลัง submit | หน้า leaderboard | เกณฑ์ Accuracy ตัวจริง |

**ถ้าทำได้แค่ข้อ 1 ก็ส่งมาก่อนเลย** อย่ารอให้ครบสาม
