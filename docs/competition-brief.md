# ARC Prize 2026 — Competition Brief

**วันที่ retrieve ข้อมูลทั้งหมดในเอกสารนี้: 2026-09-10** (ทุก section ใช้วันนี้ เว้นแต่ระบุไว้เป็นอย่างอื่น)
**เหลือเวลาถึง final submission deadline (2 พ.ย. 2026): ~53 วัน | ถึง paper deadline (10 พ.ย. 2026 06:59 GMT+7): ~61 วัน**

---

## 0. หมายเหตุเรื่องแหล่งข้อมูล — อ่านก่อน

Session นี้อยู่หลัง network egress proxy ที่ **block โดเมนหลักหลายตัว** ผลคือ verify ได้ไม่เท่ากันทุกข้อ ต้องแยกให้ชัด:

| โดเมน | สถานะ | ผล |
|---|---|---|
| `raw.githubusercontent.com` / `github.com` | ✅ เข้าถึงได้ | อ่าน primary source ของ ARC Prize Foundation ได้เต็ม |
| `arcprize.org`, `docs.arcprize.org` | ❌ EGRESS_BLOCKED (403 CONNECT) | อ่านตรงไม่ได้ |
| `www.kaggle.com` | ❌ EGRESS_BLOCKED | อ่านตรงไม่ได้ |
| `arxiv.org` | ❌ EGRESS_BLOCKED | อ่าน technical report ตรงไม่ได้ |

**ระบบ tag ความน่าเชื่อถือที่ใช้ทั้งเอกสาร:**

- **[P] — Primary, ดึงตรงมาอ่านเอง** จาก repo ของ ARC Prize Foundation บน GitHub (`arcprize/docs` คือ source ของ `docs.arcprize.org`, `arcprize/ARC-AGI-3-Kaggle-Starter`, `arcprize/ARC-AGI-3-Agents`) → **เชื่อถือได้สูงสุดในเอกสารนี้**
- **[S] — ผ่าน search-engine summary ของหน้า primary** (arcprize.org / kaggle.com) เนื้อหามาจากหน้าจริง แต่ผ่านการสรุปอีกชั้น **ยังไม่ได้อ่าน raw ด้วยตาตัวเอง** → ต้องเปิดหน้าจริงยืนยันซ้ำก่อนใช้ตัดสินใจเรื่องเงิน/กติกา
- **[C] — Community / secondary** (repo ของบุคคลที่สาม, บล็อก, aggregator) → ใช้ประกอบเท่านั้น

> ทุกอย่างที่ verify ไม่ได้ อยู่ใน section 9 ไม่มีการเดาหรือเติมจากความจำ

---

## 1. ARC-AGI-3 — track หลัก (ลำดับความสำคัญ #1)

### 1.1 SDK / repo / docs — จุดเริ่มต้นสำหรับลงมือ

นี่คือสิ่งที่ต้องใช้เริ่ม build ทันที:

| สิ่งที่ต้องใช้ | ที่อยู่ | หมายเหตุ |
|---|---|---|
| **Kaggle starter kit (ใช้ submit จริง)** | `https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter` | **จุดเริ่มต้นหลัก** — dev kit ที่แก้ไฟล์เดียวแล้ว submit ได้ [P] |
| **Agent framework (research/local)** | `https://github.com/arcprize/ARC-AGI-3-Agents` | framework สำหรับ build + test agent [P] |
| **Docs source (mirror ของ docs.arcprize.org)** | `https://github.com/arcprize/docs` | ไฟล์ `.mdx` ทั้งหมด อ่านผ่าน raw.githubusercontent ได้ [P] |
| **หน้า docs การแข่ง** | `https://docs.arcprize.org/arc-prize-2026` | ตัวหน้าเว็บ block แต่ source อยู่ที่ `arcprize/docs/arc-prize-2026.mdx` [P] |
| **API key** | `https://arcprize.org/platform` → login Google/GitHub → profile มุมขวาบน → "API Keys" | [P] จาก `api-keys.mdx` |
| **Game engine** | `https://github.com/arcprize/ARCEngine` | "Simple Python Game Engine", MIT [P] |

**ข้อกำหนดสภาพแวดล้อม:** ต้องใช้ **Python 3.12** (บังคับ เพราะ dependency ของ package `arc-agi`) และ **ไม่ต้องมี GPU** สำหรับ starter agent — ที่มา: `arcprize/docs/arc-prize-2026.mdx` [P] (https://raw.githubusercontent.com/arcprize/docs/main/arc-prize-2026.mdx)

Package manager ที่ repo ใช้คือ **`uv`** — ที่มา: `arcprize/docs/agents-quickstart.mdx` [P] (https://raw.githubusercontent.com/arcprize/docs/main/agents-quickstart.mdx)

### 1.2 Observation — หน้าตาของสิ่งที่ agent เห็น

ที่มาทั้งบล็อกนี้: `arcprize/docs/game-schema.mdx` [P] — https://raw.githubusercontent.com/arcprize/docs/main/game-schema.mdx

- **Grid ขนาดสูงสุด 64×64** (ระบุตรงว่า "Maximum 64x64 grid size")
- **ค่าในแต่ละ cell เป็น integer 0–15** แทน state/สีต่างกัน (16 ค่า) — ไม่ใช่ภาพ RGB, ไม่ใช่ pixel buffer
- **ระบบพิกัด `(0,0)` อยู่มุมซ้ายบน, รูปแบบ `(x,y)`**
- แต่ละ response มี **"one or more 2D frame arrays"** บวก **game-state metadata** → สังเกตว่าเป็น *frames* พหูพจน์ ไม่ใช่ frame เดียว
- **Game state มี 4 ค่า:** `NOT_PLAYED`, `NOT_FINISHED`, `WIN`, `GAME_OVER`

ใน Kaggle starter, signature ของ agent รับ `frames` (ทั้งหมด) และ `latest_frame` แยกกัน — ที่มา: `ARC-AGI-3-Kaggle-Starter/README.md` [P]

> ⚠️ schema แบบ field-by-field ครบทุก field (ชนิดข้อมูลของ `score`, ชื่อ field ที่แน่นอนใน response object) **ไม่ได้อยู่ในหน้า `game-schema.mdx`** — ดู section 9

### 1.3 Action space — พื้นที่การกระทำ

ที่มาทั้งบล็อกนี้: `arcprize/docs/actions.mdx` [P] — https://raw.githubusercontent.com/arcprize/docs/main/actions.mdx

**รวม 8 actions (นับ `RESET` ด้วย):**

| Action | ความหมาย | รับพิกัด? |
|---|---|---|
| `RESET` | เริ่ม/รีสตาร์ท game state | ไม่ |
| `ACTION1` | simple action (map เชิงความหมาย = up) | ไม่ |
| `ACTION2` | simple action (= down) | ไม่ |
| `ACTION3` | simple action (= left) | ไม่ |
| `ACTION4` | simple action (= right) | ไม่ |
| `ACTION5` | simple action (interact / select / rotate ฯลฯ) | ไม่ |
| `ACTION6` | **coordinate-based action** | ✅ `x`, `y` ช่วง **0–63** (grid 64×64) |
| `ACTION7` | undo | ไม่ |

**สิ่งที่สำคัญต่อการเขียน agent:**
- **มีแค่ `ACTION6` ตัวเดียวที่รับพิกัด** ดังนั้น action space จริง = 7 discrete + 1 ตัวที่มี 64×64 = 4,096 ตัวเลือกย่อย
- ทุก game response มี field **`available_actions`** บอกว่า state ปัจจุบันทำอะไรได้บ้าง → **ควรอ่าน field นี้เสมอ อย่า hard-code**
- ใน **game-over state เหลือแค่ `RESET` ที่ valid** action อื่นจะได้ **HTTP 400**
- semantics ที่ระบุ (up/down/left/right) เป็นการ map "เชิงความหมาย" — เอกสารเขียนว่า *semantically mapped* ไม่ได้รับประกันว่าทุกเกมตีความเหมือนกัน

### 1.4 การเชื่อมต่อ environment

- มี **2 ทาง** ตาม `ARC-AGI-3-Agents/README.md` [P] (https://raw.githubusercontent.com/arcprize/ARC-AGI-3-Agents/blob/main/README.md):
  1. **Cloud API** — เรียก API ของเว็บ ARC-AGI-3 ด้วย `ARC_API_KEY`
  2. **Local execution** — รัน environment ในเครื่องผ่าน ARC-AGI toolkit
- env vars ที่เกี่ยวข้อง: `ARC_API_KEY` (บังคับ), `ONLINE_ONLY=True` (บังคับใช้เฉพาะ cloud API/Replays), `AGENTOPS_API_KEY` (optional monitoring) [P]
- รันแบบ CLI: `uv run main.py --agent=random --game=ls20` [P]
- ฝั่ง toolkit เป็น **object-based ไม่ใช่ gym-style**: `from arc_agi import Arcade, OperationMode` — ที่มา `arcprize/docs/toolkit/competition_mode.mdx` [P] (https://raw.githubusercontent.com/arcprize/docs/main/toolkit/competition_mode.mdx)
- มี REST API พร้อม OpenAPI spec (`arc3v1.yaml`) ตาม navigation ใน `arcprize/docs/docs.json` [P]

### 1.5 API key และ rate limit ของ dev environment

- **วิธีขอ key:** ไปที่ `arcprize.org/platform` → login ด้วย Google หรือ GitHub → profile มุมขวาบน → section "API Keys" → generate — ที่มา `api-keys.mdx` [P] (https://raw.githubusercontent.com/arcprize/docs/main/api-keys.mdx)
- **key ปลดล็อกอะไร:** track progress ข้าม games/sessions ได้ และ **"Access the full list of games"** — เอกสารระบุว่า key ให้ "access to the full set of public games available on the platform" [P]
- **เก็บ key ไว้ใน** env var `ARC_API_KEY` หรือไฟล์ `.env` → toolkit โหลดเองตอน init `Arcade` [P]
- **Rate limit: 600 requests per minute (RPM)** เกินแล้วได้ HTTP **429** ข้อความ "rate limit has been exceeded"; API มี exponential backoff ในตัว; ขอเพิ่ม limit ได้ที่ `team@arcprize.org` subject "Increase Rate Limits" — ที่มา `rate_limits.mdx` [P] (https://raw.githubusercontent.com/arcprize/docs/main/rate_limits.mdx)

> 600 RPM = 10 req/sec ถือว่าค่อนข้างกว้างสำหรับ dev คนเดียว ไม่น่าเป็นคอขวด

### 1.6 จำนวนเกมและ level

- **จำนวนเกมทั้งหมด: ไม่ระบุใน docs** [P] — `available-games.mdx` ไม่บอกตัวเลขรวม
- **ตัวอย่าง game id ที่ระบุ:** `ls20` (Agent reasoning), `ft09` (Elementary Logic), `vc33` (Orchestration) [P] (https://raw.githubusercontent.com/arcprize/docs/main/available-games.mdx)
- **3 เกมเปิดให้ anonymous user** หลัง launch, ที่เหลือของ public set ต้องมี API key [P]
- **จำนวน level ต่อเกม: ไม่ระบุใน docs** [P]
- **Hidden evaluation set แยกจาก public set:** local `make play-local` ใช้ public dataset ส่วน Phase B บน Kaggle ใช้ **hidden games** — ที่มา `ARC-AGI-3-Kaggle-Starter/README.md` [P]
- ARC Prize บอกว่า benchmark เป็น "หลายร้อย original turn-based environments ที่ human game designer ทำมือ" [S] (https://arcprize.org/competitions/2026/arc-agi-3)
- ดูรายการเกมได้ที่ `arcprize.org/tasks` หรือ list ผ่าน toolkit [P]

### 1.7 ⭐ Scoring — actions มีผลต่อคะแนนจริง (ยืนยันแล้ว)

**ยืนยันความเข้าใจของผู้เข้าแข่ง: จำนวน action ที่ใช้เข้าสูตรคะแนนโดยตรง ไม่ใช่แค่ ชนะ/แพ้**

ที่มาทั้งบล็อกนี้: `arcprize/docs/methodology.mdx` [P] — https://raw.githubusercontent.com/arcprize/docs/main/methodology.mdx

สองคำถามที่ระบบถาม: *"How many levels did the AI complete in each game?"* และ *"How many actions did the AI take compared to humans?"*

**สูตรต่อ level:**
```
level_score = (human_baseline_actions / ai_actions) ^ 2
```

- **เพดานต่อ level = 1.15× human baseline** ("The maximum score per level is capped at 1.15x human baseline")
- **คะแนนต่อเกม** = weighted average ของ per-level scores โดย **ใช้เลข level แบบ 1-indexed เป็นน้ำหนัก** (level ท้าย ๆ มีน้ำหนักมากกว่า)
- **ทำไม่ครบทุก level → เพดานคะแนนของเกมนั้นลดลงตามส่วน**
- **คะแนนรวม = ค่าเฉลี่ยของคะแนนทุกเกม** ช่วง 0–100%
- **สำคัญมาก: tool calls และ reasoning steps ภายใน ไม่นับเป็น action** ("Internal operations like tool calls and reasoning steps do not count as actions")

**นัยเชิงวิศวกรรม 3 ข้อ:**
1. เพราะเป็น **กำลังสอง** การใช้ action เกิน baseline 2 เท่าทำให้เหลือคะแนน 25% ไม่ใช่ 50% → **ค่าปรับจากการเดามั่วรุนแรงมาก**
2. เพราะ **internal reasoning ไม่นับ** → คิดเยอะก่อนลงมือ "ฟรี" ในเชิงคะแนน (จำกัดด้วย wall-clock เท่านั้น) → สถาปัตยกรรมที่ควรเลือกคือ **คิดหนัก-กดน้อย** ไม่ใช่ reactive policy ที่กดถี่ ๆ
3. เพราะ **น้ำหนักตามเลข level** → การผ่าน level ลึกมีค่ามากกว่าการ optimize level 1 ให้เนียน

### 1.8 Competition Mode — ข้อจำกัดที่ Kaggle บังคับอัตโนมัติ

ที่มา: `arcprize/docs/toolkit/competition_mode.mdx` [P] — https://raw.githubusercontent.com/arcprize/docs/main/toolkit/competition_mode.mdx

- **จำเป็นต่อการขึ้น Unverified leaderboard**
- เปิดด้วย `Arcade(operation_mode=OperationMode.COMPETITION)` หรือ env `OPERATION_MODE=COMPETITION`
- **Kaggle Competition บังคับ mode นี้ให้อัตโนมัติ ไม่ต้องตั้งเอง**
- ข้อจำกัดที่บังคับ:
  - โต้ตอบ environment ผ่าน **API เท่านั้น** ห้ามเข้าถึงตรง
  - **คิดคะแนนทุก environment ที่มี ไม่ว่าจะลงเล่นหรือไม่** → เกมที่ข้ามไป = 0 ไม่ใช่ "ไม่นับ"
  - **อนุญาตเฉพาะ _Level Resets_ ห้าม _Game Resets_** (game reset จะถูกแปลงเป็น level reset)
  - โต้ตอบ environment ได้ **ครั้งเดียวต่อ environment** ผ่าน function `make`
  - เปิด **Scorecard ได้ใบเดียว**
  - **`get_scorecard` ถูกปิด** → ดูคะแนนสดระหว่างรันไม่ได้

> ข้อ "คิดคะแนนทุก environment ไม่ว่าจะเล่นหรือไม่" + "โต้ตอบได้ครั้งเดียวต่อ environment" เป็นข้อจำกัดออกแบบที่แรงที่สุด — วาง budget เวลาต่อเกมผิด = เสียคะแนนเกมที่เหลือทั้งหมด

### 1.9 การ submit บน Kaggle

ที่มาทั้งบล็อกนี้: `ARC-AGI-3-Kaggle-Starter/README.md` [P] — https://raw.githubusercontent.com/arcprize/ARC-AGI-3-Kaggle-Starter/blob/main/README.md

**Agent interface — แก้แค่ไฟล์เดียว `agent/my_agent.py`:**
```python
class MyAgent(Agent):
    def is_done(self, frames, latest_frame) -> bool:
        """Return True when your agent wants to stop playing."""

    def choose_action(self, frames, latest_frame) -> GameAction:
        """Look at the game state and return the next action."""
```
แก้เฉพาะ body ของ 2 method ที่เหลือ orchestration อัตโนมัติทั้งหมด

**คำสั่ง:** `make setup` (ติดตั้ง) → `make play-local` (ทดสอบกับเกม public ในเครื่อง) → `make submit` (build notebook + push ขึ้น Kaggle) → `make status` (ดูสถานะ)

**Submission 2 เฟส:**
- **Phase A — Code Validation:** `make submit` แล้ว Kaggle รันโค้ดเช็คว่าไม่ error
- **Phase B — Scoring:** ต้องไปที่ kernel บน kaggle.com กด **"Submit to Competition"** แล้วเลือกไฟล์ **`submission.parquet`** จาก output → ถึงจะได้คะแนนจริงกับ hidden game set
- **โควตา: 5 official submissions ต่อวัน** ("You only get 5 official submissions per day")
- ไฟล์ submission **สร้างอัตโนมัติ ไม่ต้องเขียน JSON/parquet เอง**

**Accelerator (แก้ที่ `scripts/build_notebook.py`):**

| ค่า | ฮาร์ดแวร์ | หมายเหตุ |
|---|---|---|
| `"cpu"` | ไม่มี GPU | agent ที่ไม่ใช้ ML |
| `"t4"` **(default)** | **2× Nvidia T4** | โมเดลเล็ก, iterate ปกติ |
| `"p100"` | Nvidia P100 | GPU เดี่ยว memory สูง |
| `"rtx6000"` | Nvidia RTX 6000 | ML หนัก — **เปิดให้เฉพาะ ARC-AGI-3** |

**🔴 Internet: ปิด** — เอกสารระบุตรงว่า **"All accelerated Kaggle sessions have internet disabled"** และ starter kit ตั้งค่านี้เป็น default อยู่แล้ว → **เรียก external API ระหว่าง submission run ไม่ได้** [P]

### 1.10 เงินรางวัลและกำหนดการ ARC-AGI-3

| รายการ | จำนวน | เงื่อนไข |
|---|---|---|
| **รวม track** | **$850,000** | [S] (https://arcprize.org/competitions/2026/arc-agi-3) |
| Grand Prize | $700,000 | agent แรกที่ทำได้ **100%** บน private eval; ถ้าไม่มีใครได้ ยกยอดไปปีถัดไป [S] |
| Top Score Award | $75,000 | แบ่งใน **top 5** ตอนจบ [S] |
| Milestone #1 (30 มิ.ย. 2026) | $37,500 | 1st $25K / 2nd $10K / 3rd $2.5K [S] (https://arcprize.org/blog/arc-prize-2026-milestone-1) |
| Milestone #2 (30 ก.ย. 2026) | $37,500 | 1st $25K / 2nd $10K / 3rd $2.5K [S] |

($700K + $75K + $75K = $850K ตรงกับยอดรวม)

**Milestone #2 คือ 30 ก.ย. 2026 — อีกประมาณ 20 วันจากวันนี้** และต้อง **open source ภายใน milestone deadline** ถึงจะมีสิทธิ์รับเงิน milestone [S] (https://arcprize.org/competitions/2026)

**กำหนดการ:** เปิด **25 มี.ค. 2026** (launch event ที่ Y Combinator HQ, San Francisco) → ปิดรับ submission **2 พ.ย. 2026** → ประกาศผล **4 ธ.ค. 2026** [S] (https://arcprize.org/competitions/2026/arc-agi-3, https://arcprize.org/blog/arc-agi-3-launch)

---

## 2. Paper Track

**Retrieve: 2026-09-10.** หมายเหตุ: หน้า Kaggle และ arcprize.org ของ track นี้ block ทั้งคู่ → ทั้ง section เป็น **[S]** ต้องเปิดหน้าจริงยืนยันก่อนพึ่งพา

### 2.1 "Writeup" submission คืออะไร — รูปแบบและความยาว

ที่มา: [S] https://www.kaggle.com/competitions/arc-prize-2026-paper-track และ https://arcprize.org/competitions/2026/paper

**ขั้นตอน:** ต้อง**ส่ง entry ให้ ARC-AGI-2 หรือ ARC-AGI-3 ให้เสร็จก่อน** → login Kaggle → ไปหน้า ARC Prize 2026 Paper Track → กดปุ่ม **"New Writeup"**

**องค์ประกอบที่ต้องมี:**

| ส่วน | บังคับ? | รายละเอียด |
|---|---|---|
| **Kaggle Writeup** | ✅ บังคับ | รายงานโครงการ **สูงสุด 1,500 คำ** วิเคราะห์ submission ของตัวเองใน ARC-AGI-2/3 |
| **Media Gallery** | ✅ บังคับ | รูปและ/หรือวิดีโอ **ต้องมี cover image** |
| **Public Kaggle Notebook** | ✅ บังคับ | โค้ด เปิดสาธารณะ **ห้ามมี login หรือ paywall** |
| **PDF Paper** | ⬜ optional | อัปโหลดผ่านฟีเจอร์ "Public Project Link" |

> **1,500 คำ ไม่ใช่ full academic paper** — เป็น structured writeup บนแพลตฟอร์ม Kaggle ส่วน PDF ฉบับเต็มเป็น *ของแถม* ไม่ใช่ตัวหลัก

**โครงสร้างเนื้อหาที่แนะนำ** (จาก guidance ของ François Chollet): **Abstract** (contribution คืออะไร เช่น "we present a method to solve ARC-AGI, with the following characteristics...") → **Intro** (ARC-AGI คืออะไร ทำไมสำคัญ แรงบันดาลใจของวิธีนี้) → **Prior Work** → **Approach** [S] (https://twitter.com/arcprize/status/1855335419358883932)

### 2.2 ⭐ ต้องผูกกับ code submission หรือไม่ — ต้อง (ยืนยัน)

**Paper ยืนอิสระไม่ได้** ทุกแหล่งตรงกัน:

- "Paper submissions must be linked to a Kaggle code submission (ARC-AGI-2 or ARC-AGI-3 track) that demonstrates the approach detailed in the paper" [S]
- "Each paper must include a corresponding Kaggle submission confirming it describes a real, working entry" [S]
- ขั้นตอนบนหน้า Kaggle เริ่มด้วย "ensure you have completed and submitted an entry to either ARC-AGI-2 or ARC-AGI-3" [S]

ที่มา: https://www.kaggle.com/competitions/arc-prize-2026-paper-track, https://arcprize.org/competitions/2026/paper

> **นัยตรง ๆ: การเขียน paper อย่างเดียวโดยไม่มี ARC-AGI-3 submission ที่รันได้จริง = ไม่มีสิทธิ์** paper กับ code เป็นแพ็กเดียวกัน

### 2.3 เกณฑ์ตัดสิน — 6 ข้อ ยืนยันแล้ว

**ยืนยัน 6 เกณฑ์ที่ผู้เข้าแข่งระบุ ถูกต้องทั้งหมด** ให้คะแนน **0 (ต่ำสุด) ถึง 5 (สูงสุด)** ในแต่ละข้อ และ **ถ่วงน้ำหนักเท่ากันทุกข้อ** ("evaluated equally") [S] (https://arcprize.org/competitions/2026/paper)

| # | เกณฑ์ | ความหมายตามที่ระบุ |
|---|---|---|
| 1 | **Accuracy** | performance บน leaderboard — **คะแนนจาก code submission ถูกใส่เข้ามาในข้อนี้โดยตรง** |
| 2 | **Universality** | วิธีนี้ generalize ได้ดีแค่ไหน |
| 3 | **Progress** | ช่วยผลักไปสู่ top score ของ ARC Prize มากแค่ไหน |
| 4 | **Theory** | อธิบายได้ไหมว่า *ทำไม* ถึงได้ผล |
| 5 | **Completeness** | (ชื่อเกณฑ์ยืนยันแล้ว — คำนิยามละเอียดไม่พบ ดู section 9) |
| 6 | **Novelty** | ความใหม่ของแนวทาง |

**ข้อสังเกตเชิงกลยุทธ์:** 5 ใน 6 เกณฑ์ **ไม่ขึ้นกับคะแนน leaderboard** — มีแค่ Accuracy ข้อเดียว แปลว่าคะแนน ARC-AGI-3 ต่ำ ๆ (ซึ่งตอนนี้ทุกคนก็ต่ำ ดู section 6) ไม่ได้ปิดโอกาส paper prize

### 2.4 โครงสร้างเงินรางวัลใน $450,000

| ส่วน | จำนวน | เงื่อนไข |
|---|---|---|
| Main paper prize pool | **$75,000** | รางวัลหลัก (มี 1st/2nd/3rd — **จำนวนเงินต่ออันดับหาไม่พบ** ดู section 9) [S] |
| Bonus pool | **$375,000** | เปิดให้ paper ที่ได้ **เกิน 4.5/5** บน rubric; **แบ่งเท่า ๆ กันในทุก paper ที่ผ่านเกณฑ์** [S] |
| **รวม** | **$450,000** | |

ที่มา: https://arcprize.org/competitions/2026/paper, https://www.kaggle.com/competitions/arc-prize-2026-paper-track

> โครงสร้าง bonus นี้ผิดปกติและสำคัญ: **ไม่ใช่การแข่งจัดอันดับ** — เป็น **เกณฑ์ผ่าน (threshold)** ใครทำเกิน 4.5/5 ก็เข้ากอง $375K ทั้งหมด แบ่งเท่ากัน ไม่ต้องชนะใคร

### 2.5 กำหนดส่ง

- **9 พ.ย. 2026** ตาม arcprize.org [S] (https://arcprize.org/competitions/2026/paper)
- Screenshot ที่ผู้ใช้เห็นระบุ **10 พ.ย. 2026 06:59 GMT+7** → **ตรงกัน**: 10 พ.ย. 06:59 GMT+7 = **9 พ.ย. 23:59 UTC** เป็นเวลาเดียวกัน ไม่ขัดแย้ง
- ผู้เข้าแข่งระบุ "8 พ.ย." → **ไม่ตรงกับแหล่งใด** ดู section 9

**ขนาดทีม: 1–8 คน** ("individually or in a team of up to eight (8) members") [S] (https://www.kaggle.com/competitions/arc-prize-2026-paper-track)

---

## 3. ARC-AGI-2 — track ที่ไม่ได้เลือก (สรุปสั้น)

**Retrieve: 2026-09-10.** ทั้ง section เป็น **[S]** (arcprize.org / kaggle.com block)

- **เงินรางวัลรวม $700,000**: Progress Prizes $275,000 + Grand Prize $275,000 + Bonus Prize $150,000 [S] (https://arcprize.org/competitions/2026/arc-agi-2)
- **Progress Prize รายอันดับ:** 1st $75,000 / 2nd $50,000 / 3rd $40,000 / 4th $35,000 / 5th $25,000 / 6th $20,000 / 7th $15,000 / 8th $15,000 (รวม = $275,000) [S]
- **Grand Prize ต้องได้ > 85%** บน private evaluation set [S]
- **2026 เป็นปีสุดท้ายที่ ARC-AGI-2 ใช้เป็น official Kaggle competition** [S] (https://arcprize.org/competitions/2026)
- **รูปแบบ submission:** Kaggle notebook; ทำนาย **2 outputs ต่อ test input grid ทุกอัน**; ถ้า 1 ใน 2 ตรง ground truth เป๊ะ ได้ 1 คะแนน ไม่งั้น 0 [S]
- **Internet: ปิด** — "No internet access is allowed during the automated container rerun evaluation" [S]
- **Runtime: สูงสุด 12 ชั่วโมง** CPU/GPU รวม [S]
- **Deadline: 2 พ.ย. 2026** ประกาศผล 4 ธ.ค. 2026 [S]
- **คะแนนสูงสุดบน Kaggle competition leaderboard ปี 2025: 24%** ที่ $0.20/task [S] (https://arcprize.org/blog/arc-prize-2025-results-analysis) — คะแนนปัจจุบันของ competition leaderboard 2026 ดู section 9

---

## 4. คุณสมบัติผู้เข้าแข่ง — สำคัญมากสำหรับนักเรียน ม.ปลายในไทย

**Retrieve: 2026-09-10**

### 4.1 🔴 อายุ — ประเด็นที่ต้องจัดการก่อน

**กติกามาตรฐาน Kaggle:** ผู้เข้าแข่งต้องมีอายุ **"the older of 18 years old or the age of majority in your jurisdiction of residence (unless otherwise agreed to by Competition Sponsor and appropriate parental/guardian consents have been obtained by Competition Sponsor)"** [S] (https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules)

**อ่านให้ชัด — สำหรับผู้พำนักในไทย เกณฑ์คือ "ค่าที่มากกว่า" ระหว่าง 18 กับอายุบรรลุนิติภาวะไทย:**

**อายุบรรลุนิติภาวะของไทย = 20 ปี** ตาม **มาตรา 19 ประมวลกฎหมายแพ่งและพาณิชย์** — ผู้ที่อายุครบ 20 ปีบริบูรณ์พ้นจากภาวะผู้เยาว์และมีความสามารถทางกฎหมายเต็ม [C] (https://library.siam-legal.com/thai-law/civil-and-commercial-code-natural-persons-sections-15-36/, https://legalclarity.org/thailand-legal-age-consent-drinking-and-adulthood/)

> **ผลลัพธ์: เกณฑ์ที่ใช้กับผู้เข้าแข่งในไทยคือ 20 ปี ไม่ใช่ 18 ปี** นักเรียน ม.ปลายเกือบทั้งหมดเป็น "ผู้เยาว์" ตามกฎหมายไทย และ**ตกอยู่ใน exception clause** คือต้องได้ทั้ง (ก) ความยินยอมจาก Competition Sponsor และ (ข) parental/guardian consent ที่ Sponsor เก็บไว้

**เส้นทางที่มีอยู่จริง — ไม่ใช่ทางตัน:** Kaggle มีกระบวนการรองรับผู้เยาว์เป็นเรื่องเป็นราว มีหน้าเฉพาะ 2 หน้า:
- "PARENT/GUARDIAN CONSENT FOR MINOR'S PARTICIPATION IN A KAGGLE COMPETITION" — https://www.kaggle.com/consent-minors-process [S]
- "PARENT/GUARDIAN CONSENT FOR MINOR'S USE OF KAGGLE.COM" — https://www.kaggle.com/guardian-consent-minor-use [S]

**ตอนรับรางวัล:** ถ้าผู้ชนะเป็นผู้เยาว์ **พ่อแม่หรือผู้ปกครองตามกฎหมายต้องเป็นผู้ลงนามเอกสาร** ผู้ชนะอาจต้องลงนามและส่งคืน **Declaration of Eligibility and Liability and Publicity Release** และต้องส่งคืน **ภายใน 7 วัน** นับจากที่พยายามติดต่อแจ้ง มิฉะนั้น**สละสิทธิ์รางวัล** [S] (https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules)

> ⏱️ หน้าต่าง 7 วันนี้แคบมาก — ถ้าติดอันดับเงินรางวัลแล้วเอกสารผู้ปกครองยังไม่พร้อม จะเสียสิทธิ์ ควรเตรียมล่วงหน้า ไม่ใช่รอตอนประกาศผล

### 4.2 ประเทศ — ไทยผ่าน

ข้อจำกัดถิ่นที่อยู่ตาม official rules: ห้ามผู้พำนักใน **Crimea, Donetsk People's Republic (DNR), Luhansk People's Republic (LNR), Cuba, Iran, North Korea** [S] (https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/rules, https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules)

> **ประเทศไทยไม่อยู่ในรายการห้าม** ไม่มีอุปสรรคด้านสัญชาติ/ถิ่นที่อยู่

### 4.3 ขนาดทีม

- **Paper Track: 1–8 คน** [S] (https://www.kaggle.com/competitions/arc-prize-2026-paper-track)
- **ARC-AGI-3: 1–5 คน** และ merge ทีมได้จนถึง team merger deadline [S] (https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
- เข้าแข่งคนเดียวได้ทั้งสอง track ไม่มีข้อกำหนดขั้นต่ำ
- ต้องเป็นเจ้าของบัญชี Kaggle ที่ลงทะเบียนแล้ว และ **ส่งภายใต้บัญชีเดียวเท่านั้น** [S]

---

## 5. LLM API ภายนอก, open source, และ licensing

**Retrieve: 2026-09-10**

### 5.1 🔴 External / commercial LLM API — ใช้ระหว่าง scoring ไม่ได้

**ยืนยันจาก primary source โดยตรง:** "All accelerated Kaggle sessions have internet disabled" และ starter kit ตั้งเป็น default — `arcprize/docs/arc-prize-2026.mdx` [P] (https://raw.githubusercontent.com/arcprize/docs/main/arc-prize-2026.mdx)

ยืนยันซ้ำจากหน้าการแข่ง: submission ถูกประเมินใน **sandboxed environment ที่ไม่มี internet** ซึ่ง**ตัดการเรียก hosted model อย่าง GPT / Claude / Gemini ออกทั้งหมด** และ solution ต้องรันแบบ self-contained ภายใน compute/time limit ของ Kaggle [S] (https://arcprize.org/competitions/2026, https://arcprize.org/competitions/2026/arc-agi-3)

**ใช้กับทั้ง ARC-AGI-2 และ ARC-AGI-3** [S]

> **ข้อสรุปเด็ดขาด: solver ที่เรียก external LLM API ระหว่าง submission run ส่งไม่ได้เลย** ทางเดียวคือ **โมเดล weights แบบ local** ที่แพ็กมากับ notebook/dataset ตามที่ Tufa Labs ทำ (รัน Qwen 3.6 27B FP8 ในเครื่อง — ดู section 6.2)
>
> หมายเหตุแยกให้ชัด: ข้อห้ามนี้ใช้กับ **submission run** ไม่ได้ห้ามใช้ LLM เชิงพาณิชย์ตอน **พัฒนา/วิจัย/สร้าง synthetic data ในเครื่องตัวเอง** ทีมปี 2025 ที่ชนะก็ใช้ synthetic data generation หนักมาก (section 6.1)

### 5.2 Open source — บังคับสำหรับผู้รับรางวัล

- ผู้ที่มีสิทธิ์รับรางวัล **จะถูกตัดออกจากการแข่งขันถ้าไม่ open source solution** [S] (https://arcprize.org/competitions/2026/arc-agi-2)
- **ต้อง open source artifacts ทั้งหมดและแนบกับ official competition Solution Writeup ภายใน 7 วัน** นับจาก submission deadline จึงจะมีสิทธิ์ [S]
- ต้อง **open source ก่อนได้รับคะแนน private evaluation อย่างเป็นทางการ** และใช้กับ **ทั้งสาม track** [S] (https://arcprize.org/competitions/2026)
- **Milestone prizes:** ต้อง open source **ภายในวัน milestone deadline** ถึงมีสิทธิ์รับเงิน milestone [S] (https://arcprize.org/competitions/2026)

### 5.3 License ที่ต้องใช้

- solution ที่มีสิทธิ์รับรางวัลต้องปล่อยภายใต้ **permissive หรือ public-domain license — ระบุ CC0 หรือ MIT-0** [S] (https://arcprize.org/competitions/2026/arc-agi-2, https://arcprize.org/competitions/2026/arc-agi-3)
- repo ของ ARC Prize เองใช้ **MIT** และ **Apache 2.0** [P] (https://github.com/arcprize)

> ⚠️ **MIT-0 ไม่ใช่ MIT** (MIT-0 ตัดข้อกำหนด attribution ออก) และ **CC0** คือสละลิขสิทธิ์ ควรตั้ง license ให้ถูกตั้งแต่วันแรก การเปลี่ยนทีหลังตอนมี contributor แล้วยุ่งยาก

---

## 6. Prior art — อะไรที่ได้ผลจริง

**Retrieve: 2026-09-10**

### 6.1 ARC Prize 2025 (ปีที่แล้ว — ARC-AGI-2 grid puzzles)

ที่มา [S]: https://arcprize.org/blog/arc-prize-2025-results-analysis, https://arcprize.org/competitions/2025, technical report https://arxiv.org/abs/2601.10904 (arXiv block อ่านตรงไม่ได้)

- แข่ง **26 มี.ค. – 3 พ.ย. 2025**, **1,455 ทีม**, **15,154 entries**
- **Top Kaggle score: NVARC ที่ 24%** บน ARC-AGI-2 private set ที่ **$0.20/task** — ต่อยอดจาก **ARChitects** (ผู้ชนะปี 2024) และ **ใช้ synthetic data generation หนักมาก**เพื่อยกระดับโมเดล
- **Grand Prize ยังไม่มีใครได้**
- **Paper track: ส่ง 90 papers** (เพิ่มจาก 47 ในปี 2024) คุณภาพดีจนกรรมการ**ขยายรางวัลเพิ่ม runner-up อีก 5 ราย และ honorable mention อีก 8 ราย**

**Paper award 3 อันดับแรกปี 2025:**

| อันดับ | ผู้เขียน | ผลงาน |
|---|---|---|
| 1 | Alexia Jolicoeur-Martineau | **Tiny Recursive Model (TRM)** — recursive model ~**7M parameters** ได้ ~**45% บน ARC-AGI-1** และ ~**8% บน ARC-AGI-2** |
| 2 | Julien Pourcel et al. | **SOAR** — self-improving evolutionary program synthesis ดันผลงาน open-source บน ARC-AGI-1 ขึ้นถึง **52%** |
| 3 | MindsAI | pipeline **test-time training** ที่ engineer หนัก ได้ **15.42% บน ARC-AGI-2** |

> **สัญญาณสำคัญ: TRM ที่ได้ paper award อันดับ 1 มีแค่ ~7M parameters** — paper track ให้รางวัลกับ *ความคิด* ไม่ใช่ *ขนาดโมเดล* นี่คือช่องของคนทำคนเดียวที่ไม่มี compute

### 6.2 ⭐ ARC-AGI-3 — prior art เชิง agentic (ตรงกับที่จะทำ)

**Baseline ตอนเปิดตัว (มี.ค. 2026):** มนุษย์ **100%** | frontier LLM ใช้ตรง ๆ **ต่ำกว่า 1%** (Gemini 3.1 Pro ~0.37%, Claude Opus 4.6 ~0.2%) | agent ที่สร้างมาเฉพาะทางในช่วง preview **~12.6%** — ข้อสรุปที่ระบุไว้: **"raw model scale did not buy interactive competence"** [C] (https://github.com/arodmor/arc-agi-3), [S] (https://arcprize.org/blog/arc-agi-3-launch)

**Milestone #1 (30 มิ.ย. 2026) — ผู้ชนะและวิธีการ** [S] (https://arcprize.org/blog/arc-prize-2026-milestone-1):

| อันดับ | ผู้ชนะ | เงิน | แนวทาง |
|---|---|---|---|
| 1 | **Tufa Labs** | $25K | LLM open-source ตัวเล็ก เล่น ARC-AGI-3 โดย **เขียนและรัน Python ใน live REPL** — มองแต่ละเกมเป็นโจทย์ programming แบบ interactive |
| 2 | **Reki** | $10K | **vision-language model** อ่านกระดานแล้วคืน **JSON actions** |
| 3 | **Md Boktiar Mahbub Murad** | $2.5K | agent แบบ visual-action คล้ายกัน แพ็กเป็น framework ที่ config ได้ |

**🔑 คะแนนที่ชนะ Milestone #1 คือ 1.21%** [C] (https://alphasignal.ai/news/tufa-labs-wins-25k-beating-frontier-ai-on-the-world-s-hardest-benchmark)

**Duck Harness — โซลูชันผู้ชนะ open source แล้ว:**
- Repo: **https://github.com/Tufalabs/duck-harness** — "The Duck: ARC-AGI-3 inference harness -- winning solution to ARC-AGI-3 Milestone 1"
- นิยามตัวเอง: **"a tool-using solver that plays ARC-AGI-3 games through TAAF (the Tufa ARC-AGI Framework)"** [P] (https://raw.githubusercontent.com/Tufalabs/duck-harness/main/README.md)
- 3 ส่วนประกอบ: **ARC3-Inference** (solver, prompts, artifacts, scoring, viewer) + **TAAF** (Benchmark/GameAPI execution framework) + **Example Run** (25 games × 20 passes) [P]
- รันผ่าน **local vLLM server หรือ OpenRouter**; ดู run ที่บันทึกไว้ใช้แค่ Python deps พื้นฐาน (ไม่ต้องมี GPU) แต่ **รัน harness เองต้องมี `server` extra (vLLM + Torch, หลาย GB, ต้องมี GPU)** [P]
- โมเดล: **Qwen 3.6 27B FP8 รันในเครื่อง** [C] (https://alphasignal.ai/news/..., https://tufalabs.ai/research/duck-harness/)
- **บทเรียนที่ Tufa ระบุเอง: tool ที่ hand-craft มา "กลับทำให้แย่ลง" — ปล่อยให้โมเดลด้นสดเองได้ผลดีกว่า** [C]
- เป็น **ทายาททางความคิดของ "Stochastic Goose"** ซึ่งชนะ ARC-AGI-3 Agent Preview Competition ก่อนหน้า [C]

**สถานะปัจจุบันของ Kaggle competition leaderboard:** high score **7.51% โดย CSTL** [C] (https://benchlm.ai/benchmarks/arcagi3, อ้างอิงหน้า https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/leaderboard)

**⚠️ อย่าสับสนกับ frontier verified leaderboard** ซึ่งเป็นคนละสนาม (โมเดลใหญ่ ใช้ internet และ compute ไม่จำกัด **ไม่อยู่ใต้กติกา Kaggle**): ณ 8 ก.ย. 2026 GPT-6 Astra **62.7%**, Claude Opus 5 **30.2%**, GPT-5.6 Sol **7.8%** บน ARC-AGI-3 [C] (https://benchlm.ai/benchmarks/arcagi3) — ตัวเลขเหล่านี้ **เทียบกับ 7.51% ของ Kaggle ไม่ได้**

**แหล่งอ่านเพิ่มที่ระบุตัวตนได้ (แต่ session นี้เปิดไม่ได้):**
- ARC-AGI-3 paper: https://arxiv.org/abs/2603.24621 (arXiv block)
- ARC Prize 2025 Technical Report: https://arxiv.org/abs/2601.10904 (arXiv block)
- ARC-AGI-3 sample submission notebook "Stochastic Goose": https://www.kaggle.com/code/inversion/arc3-sample-submission-stochastic-goose (Kaggle block)
- Community agent repos [C]: https://github.com/AR6420/arc-agi-3-agent, https://github.com/samrishtt/arc-agi-3-kaggle-competition, https://github.com/sonpham-org/arc-3

---

## 7. สรุปกำหนดการทั้งหมด

**Retrieve: 2026-09-10.** GMT+7 = UTC+7

| วันที่ | เหตุการณ์ | สถานะ verify |
|---|---|---|
| 25 มี.ค. 2026 | ARC Prize 2026 เปิด | [S] ยืนยัน |
| 30 มิ.ย. 2026 | ARC-AGI-3 Milestone #1 (ผ่านไปแล้ว) | [S] ยืนยัน |
| **30 ก.ย. 2026** | **ARC-AGI-3 Milestone #2** — ต้อง open source ภายในวันนี้ | [S] ยืนยัน |
| 26 ต.ค. 2026 | Entry deadline / team merger deadline | ❌ **verify ไม่ได้** — ดู section 9 |
| **2 พ.ย. 2026** | **Final submission deadline** (ARC-AGI-2 และ ARC-AGI-3) | [S] ยืนยัน |
| ~9 พ.ย. 2026 | เส้นตาย open source artifacts (ภายใน 7 วันหลัง deadline) | [S] ยืนยันกฎ, วันที่คำนวณเอง |
| **9 พ.ย. 2026 23:59 UTC = 10 พ.ย. 06:59 GMT+7** | **Paper Track submission deadline** | [S] ยืนยัน (ตรงกับ screenshot) |
| 4 ธ.ค. 2026 | ประกาศผล | [S] ยืนยัน |

---

## 8. ผลต่อการตัดสินใจ

ข้อค้นพบที่**เปลี่ยนสิ่งที่ผู้เข้าแข่งเดี่ยวควรทำจริง ๆ** (ระบุตามข้อเท็จจริง ไม่ใช่คำแนะนำ):

1. **Internet ปิดระหว่าง scoring ทั้งสอง code track** [P/S] → สถาปัตยกรรมที่เรียก external LLM API **ส่งไม่ได้** ตัวเลือกที่เหลือคือ local weights แพ็กมากับ notebook, โปรแกรมแบบ non-neural, หรือลูกผสม การตัดสินใจนี้ต้องเกิด**ก่อน**เขียนโค้ดบรรทัดแรก ไม่ใช่ตอนใกล้ส่ง

2. **Paper ยืนอิสระไม่ได้** [S] → ต้องมี ARC-AGI-3 submission ที่รันได้จริงก่อน paper จึงมีสิทธิ์ ลำดับงานถูกบังคับ: code ก่อน แล้ว paper อ้างถึง code นั้น

3. **Paper คือ Kaggle Writeup 1,500 คำ + cover image + public notebook** ไม่ใช่ full academic paper (PDF เป็น optional) [S] → งานเขียนเล็กกว่าที่คนมักคิดมาก แต่ต้องมี media gallery และ notebook สาธารณะซึ่งเป็นงานคนละแบบ

4. **Bonus $375K เป็น threshold ไม่ใช่การจัดอันดับ** — เกิน 4.5/5 แล้วแบ่งเท่ากันทุกคนที่ผ่าน [S] → ไม่ต้องชนะใครก็เข้ากองนี้ได้

5. **5 ใน 6 เกณฑ์ paper ไม่ขึ้นกับคะแนน leaderboard** (มีแค่ Accuracy) [S] → คะแนน ARC-AGI-3 ต่ำไม่ได้ปิดโอกาส paper prize

6. **Scoring ARC-AGI-3 ลงโทษ action ที่เกินจำเป็นแบบกำลังสอง แต่ internal reasoning ฟรี** [P] → สถาปัตยกรรม "คิดหนัก กดน้อย" ได้เปรียบเชิงโครงสร้างเหนือ reactive policy และการเดามั่วมีต้นทุนสูงกว่าที่สัญชาตญาณบอก

7. **Competition mode คิดคะแนนทุก environment ไม่ว่าจะเล่นหรือไม่ และโต้ตอบได้ครั้งเดียวต่อ environment** [P] → การจัดสรร budget เวลา/action ข้ามเกมเป็นปัญหาที่ต้องแก้ ไม่ใช่รายละเอียดปลีกย่อย เกมที่รันไม่ทัน = 0

8. **คะแนนที่ชนะ Milestone #1 คือ 1.21% และ high score ปัจจุบันคือ 7.51%** [S/C] → เพดานที่ต้องข้ามเพื่อติดอันดับต่ำมากในเชิงสัมบูรณ์ ต่างจาก ARC-AGI-2 ที่ SOTA อยู่ที่ 24% และมีทีมสะสมมาหลายปี

9. **อายุบรรลุนิติภาวะไทย = 20 ปี และกฎ Kaggle ใช้ "ค่าที่มากกว่า" ระหว่าง 18 กับเกณฑ์ท้องถิ่น** [S/C] → เกณฑ์ที่บังคับใช้จริงคือ **20 ปี ไม่ใช่ 18** นักเรียน ม.ปลายต้องผ่านเส้นทาง parental/guardian consent และเมื่อชนะ **ผู้ปกครองต้องลงนามเอกสารภายใน 7 วัน** มิฉะนั้นสละสิทธิ์ — เป็นงานเอกสารที่ต้องเตรียมล่วงหน้า ไม่ใช่ตอนประกาศผล **ประเทศไทยไม่อยู่ในรายการประเทศต้องห้าม**

10. **ต้อง open source ภายใต้ CC0 หรือ MIT-0 ก่อนได้รับคะแนน private evaluation อย่างเป็นทางการ** [S] → ตั้ง license ให้ถูกตั้งแต่ commit แรก และ MIT-0 ≠ MIT

11. **Milestone #2 คือ 30 ก.ย. 2026 (อีก ~20 วัน)** [S] → มีจุดตัดสินเงินรางวัลก่อน deadline หลัก 33 วัน โดยต้อง open source ภายในวันนั้น

12. **โซลูชันผู้ชนะ Milestone #1 เปิด source ครบแล้ว** (https://github.com/Tufalabs/duck-harness) [P] → มี reference implementation ที่ชนะจริงให้ศึกษา พร้อมบทเรียนที่ผู้ชนะระบุเองว่า hand-crafted tools ทำให้ผลแย่ลง

---

## 9. ยังไม่ยืนยัน / verify ไม่ได้

**ทุกข้อในนี้คือสิ่งที่หาแหล่งยืนยันไม่ได้ในการค้นครั้งนี้ ไม่มีการเดา**

### 9.1 บล็อกโดยระบบ (เข้าถึงไม่ได้เชิงเทคนิค)
- **`arcprize.org`, `docs.arcprize.org`, `www.kaggle.com`, `arxiv.org` ถูก block โดย network egress proxy** (403 ที่ CONNECT tunnel) → ทุกข้อที่ tag **[S]** มาจาก search-engine summary ของหน้าเหล่านี้ **ไม่ได้อ่าน raw ด้วยตาตัวเอง** ก่อนตัดสินใจเรื่องเงินหรือกติกา ควรเปิดหน้าจริงยืนยัน
- โดเมนรองที่ลองแล้ว block เช่นกัน: `competehub.dev`, `scholarships.af`

### 9.2 ARC-AGI-3 — ช่องว่างทางเทคนิค
- **Response schema แบบเต็ม field-by-field**: `game-schema.mdx` ระบุเองว่าไม่ได้ให้ชื่อ field และชนิดข้อมูลครบ, ไม่ได้ให้รูปแบบ/ชนิดของ `score`, และไม่ได้ให้รายละเอียด frame encoding เกินกว่า "integer 0–15" → ต้องอ่านจาก OpenAPI spec `arc3v1.yaml` ใน repo `arcprize/docs` หรือ source ของ `arc_agi` package
- **รูปแบบ request ที่แน่นอนสำหรับส่ง `ACTION6` พร้อมพิกัด** (query param / JSON body / อื่น ๆ) — `actions.mdx` ไม่ระบุ
- **จำนวนเกมทั้งหมด** และ **จำนวน level ต่อเกม** — ไม่ระบุใน docs (ระบุเพียงว่า "หลายร้อย environments" [S])
- **Public/dev games ต่างจาก hidden evaluation set อย่างไรในเชิงโครงสร้าง** — `available-games.mdx` ไม่ชี้ชัด
- **API key ฟรีหรือมีค่าใช้จ่าย** — `api-keys.mdx` ไม่ระบุราคา
- **ขีดจำกัดขนาดโมเดล / package ที่ใช้ได้บน Kaggle สำหรับ ARC-AGI-3** — `ARC-AGI-3-Kaggle-Starter/README.md` ระบุว่า "No model size limits or package restrictions are specified"
- **Agent base class interface แบบเต็ม** ใน `ARC-AGI-3-Agents` — README ไม่ได้ให้สเปกละเอียด (ต่างจาก Kaggle starter ที่ให้ 2 method ชัดเจน)
- **License ของ duck-harness** — ไม่ระบุใน README
- **human_baseline_actions หาค่าได้จากไหน / เปิดเผยหรือไม่** — `methodology.mdx` ใช้ตัวแปรนี้ในสูตรแต่ไม่บอกว่าเข้าถึงค่าได้อย่างไร **นี่เป็นช่องว่างที่กระทบการ optimize โดยตรง**

### 9.3 ⚠️ ความขัดแย้งของข้อมูล (ต้องตัดสินด้วยหน้าจริง)
- **Runtime limit ของ ARC-AGI-3:** พบทั้ง **"9-hour budget"** และ **"ต้องรันน้อยกว่า 12 ชั่วโมง"** ในการค้นเดียวกัน [S] (https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview/code-requirements) ซ้อนกับกติกาทั่วไปของ Kaggle ที่ GPU session cap 9 ชม. และ CPU 12 ชม. แต่มีประกาศ product update ว่าขยาย GPU เป็น 12 ชม. แล้ว (https://www.kaggle.com/product-feedback/302908) → **ตัวเลขที่ผู้เข้าแข่งระบุ (9 ชม.) มีแหล่งรองรับ แต่ไม่ใช่ข้อสรุปเดียว ยังไม่ถือว่ายืนยัน**
- **ยอดเงิน milestone:** โพสต์ X ของ ARC Prize ระบุ **"$35K milestone prize"** (https://x.com/arcprize/status/2059685409102446880) ขณะที่หน้าการแข่งให้ตัวเลข **$25K + $10K + $2.5K = $37.5K** [S] → ต่างกัน $2.5K
- **ขนาดทีม:** Paper Track ระบุ **สูงสุด 8 คน** ส่วน ARC-AGI-3 ระบุ **1–5 คน** [S] → ไม่จำเป็นต้องขัดกัน (คนละ track) แต่ยังไม่ได้ยืนยันจากหน้าเดียวกัน
- **"~12.6%" ของ preview agent เทียบกับ "7.51%" ของ Kaggle leaderboard ปัจจุบัน** — น่าจะคนละเงื่อนไขการวัด (preview vs competition mode) แต่**ยังไม่พบคำอธิบายที่ระบุชัด**

### 9.4 กำหนดการที่ยืนยันไม่ได้
- **Entry deadline 26 ต.ค. 2026** ที่ผู้เข้าแข่งระบุ — **หาแหล่งยืนยันไม่ได้** พบเพียงว่า "team mergers are allowed until the deadline" โดยไม่ระบุวันที่ [S] → ต้องเช็คหน้า Kaggle จริง (entry/team-merger deadline เป็นเส้นตายที่พลาดแล้วแก้ไม่ได้)
- **Paper deadline 8 พ.ย. 2026** ที่ผู้เข้าแข่งระบุ — **ไม่ตรงกับแหล่งใด** ทุกแหล่งชี้ไปที่ 9 พ.ย. 2026 (= 10 พ.ย. 06:59 GMT+7 ตรงกับ screenshot) → **ถ้ายึด 8 พ.ย. จะเผื่อเวลาเกินจริง 1 วัน ซึ่งไม่เป็นอันตราย แต่ตัวเลขไม่ถูกต้อง**

### 9.5 Paper Track — รายละเอียดที่ยังขาด
- **จำนวนเงินรายอันดับใน $75,000** (1st/2nd/3rd ได้เท่าไร) — ไม่พบ
- **คำนิยามละเอียดของเกณฑ์ "Completeness"** — ชื่อเกณฑ์ยืนยันแล้ว แต่คำอธิบายไม่พบ (5 ข้อที่เหลือมีคำอธิบายสั้น ๆ)
- **จำนวนหน้าสูงสุดของ PDF (optional)** — ไม่พบ; ที่ยืนยันคือ **1,500 คำ** ของตัว Kaggle Writeup
- **กระบวนการตัดสินโดยละเอียด** (กรรมการกี่คน, peer review หรือไม่, ตัดสินอย่างไรเมื่อคะแนนเท่ากัน) — ไม่พบ
- ตัวเลขจาก screenshot ของผู้ใช้ (6,890 entrants / 184 participants / 180 teams / 195 submissions สำหรับ Paper Track; 13,906 / 3,178 / 2,936 / 32,339 สำหรับ ARC-AGI-3) — **ยืนยันไม่ได้** เพราะ Kaggle block; เป็นตัวเลขที่เปลี่ยนตลอดเวลาอยู่แล้ว

### 9.6 อื่น ๆ
- **คะแนนสูงสุดปัจจุบันบน ARC-AGI-2 Kaggle competition leaderboard ปี 2026** — ไม่พบ (ตัวเลข 24% เป็นของ**ปี 2025**; ตัวเลข 90–95% ที่ปรากฏเป็นของ **frontier verified leaderboard** ซึ่งเป็นคนละสนาม ไม่มีข้อจำกัด compute/internet)
- **ตัวเลขจาก benchlm.ai และ alphasignal.ai** เป็น aggregator บุคคลที่สาม [C] — ยืนยันกับ `arcprize.org/leaderboard` ไม่ได้เพราะโดน block
- **ARC Prize เคยอนุมัติข้อยกเว้นให้ผู้เยาว์เข้าแข่งจริงหรือไม่** — พบเพียงว่ากติกา*เปิดช่อง*ไว้และ Kaggle มีกระบวนการรองรับ **ไม่พบกรณีตัวอย่างจริง** ประเด็นนี้ควรถาม `team@arcprize.org` โดยตรง
