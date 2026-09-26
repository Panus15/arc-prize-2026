# ARC Prize 2026

การเข้าแข่ง **ARC Prize 2026** — agent สำหรับ **ARC-AGI-3** และ writeup สำหรับ **Paper Track**
พร้อมเส้นฐานที่วัดจริงบน **ARC-AGI-2**

> **ปิดรับ 10 พ.ย. 2026 · 06:59 GMT+7**
> ⚠️ **Milestone #2: 30 ก.ย. 2026** — ต้อง open source ภายในวันนั้น

## สถานะ

| ส่วน | สถานะ |
|---|---|
| ARC-AGI-2 loader + evaluation harness | ✅ เสร็จ |
| ARC-AGI-2 rule baselines (14 ตัว) | ✅ วัดจริงแล้ว — `docs/baselines.md` |
| สถิติชุดข้อมูล · สืบกติกา | ✅ `docs/dataset-analysis.md` · `docs/competition-brief.md` |
| **ARC-AGI-3 agent** | ✅ **250 เทสผ่าน** · เล่นกระดานจริง 500 รอบไม่พังเลย → `agi3/` |
| **Paper Track writeup** | 🟡 §2–8 ครบ (1,432 คำ) · §1 ปิดท้าย + §8 รอผลเกมสด |
| **cover image + public notebook** | ✅ `paper/cover.png` · `paper/notebook.ipynb` (รันได้ไม่ต่อเน็ต) |
| **Kaggle submission (ARC-AGI-3)** | 🟡 notebook พร้อมอัปโหลด · จำลอง Kaggle ครบ 2 รอบผ่าน · **ยังไม่ได้ submit** |
| **เกมจริง** | ⛔ ยังไม่เคยรัน — ต้องดาวน์โหลดไฟล์เกมครั้งเดียวจากเครื่องที่ต่อ `arcprize.org` ได้ |
| **สิทธิ์เข้าแข่ง (ผู้เยาว์)** | ⛔ ต้องถาม Sponsor · ร่างอีเมลพร้อมส่งที่ [`docs/eligibility-minor.md`](docs/eligibility-minor.md) |

**สิ่งที่เจ้าของโครงการต้องทำ ทีละขั้น: [`docs/YOUR-STEPS.md`](docs/YOUR-STEPS.md)**

แผนงานเต็ม สิ่งที่ทำแล้วพร้อมผล และสิ่งที่เหลือ: [`docs/ROADMAP.md`](docs/ROADMAP.md)

## ผลที่วัดได้แล้ว

**ARC-AGI-3 — ช่องว่างระหว่างห้องทดลองกับสนามจริง** ([`docs/simulation-gap.md`](docs/simulation-gap.md))

```
policy       learns?      quiet mock    noise-calibrated mock
-------------------------------------------------------------
random            no     lost 2/3            lost 2/3
greedy            no      WIN 3/3             WIN 3/3
explorer         yes      WIN 3/3            lost 0/3
navigator        yes      WIN 3/3            lost 0/3
```

**noise ทำลายเฉพาะวิธีที่เรียนรู้** — สองตัวที่ไม่เรียนรู้อะไรเลยให้ผลเท่าเดิมเป๊ะทั้งสองสนาม
และบนกระดานที่มี noise **การสุ่มมั่วชนะ agent ที่ตั้งใจออกแบบทั้งสองตัวของเรา**
สนามที่ทั้งสองตัวแพ้นั้น calibrate มาจากการรันจริง 500 ครั้ง — การตรงกับสถิติที่วัดได้
จึงยังไม่พอจะทำให้ simulator เชื่อถือได้

**ARC-AGI-2 — เส้นฐาน** ([`docs/baselines.md`](docs/baselines.md))

rule-based solver ทั้ง 14 ตัวได้ **0.00% บนชุด evaluation** (0 จาก 120 ข้อ)
ขณะที่ composite ได้ **7.70% บน training** (77 จาก 1000)

ผลวินิจฉัยที่สำคัญกว่า: บน training กฎที่ fit ได้ตอบถูก **77/77 (100%)** แต่บน evaluation
**ไม่มีกฎไหน fit ได้แม้แต่ข้อเดียว** — กฎไม่ได้ตอบผิด แต่ใช้ไม่ได้เลย
แปลว่าการเพิ่มกฎแบบเดิมจะยังได้ 0% ต้องเปลี่ยนประเภทวิธี ไม่ใช่เพิ่มปริมาณ

## โครงสร้าง

```
arc-prize-2026/
├── docs/                     ทุกไฟล์มีตัวเลขที่วัดจริง + คำสั่งทำซ้ำ
│   ├── YOUR-STEPS.md         สิ่งที่เจ้าของโครงการต้องทำ ทีละขั้น
│   ├── ROADMAP.md            แผนงาน · สิ่งที่ทำแล้วและผล · สิ่งที่เหลือ  ← เริ่มอ่านที่นี่
│   ├── simulation-gap.md     ผลหลักของโครงงาน
│   ├── competition-brief.md  กติกาทั้ง 3 สนาม พร้อมแหล่งอ้างอิงรายข้อ
│   ├── baselines.md          ผลวัด baseline จริง
│   └── dataset-analysis.md   สถิติ ARC-AGI-2 ทั้ง 1,120 task
├── arc2/                     งาน ARC-AGI-2 (loader, harness, solvers, tests)
├── agi3/                     ARC-AGI-3 agent — สนามหลัก · submission/kaggle/ = notebook พร้อมส่ง
└── paper/                    writeup · notebook · cover · ข้อมูลที่ฝังไปกับเปเปอร์
```

## เริ่มใช้งาน (ส่วน ARC-AGI-2)

```bash
cd arc2
./setup.sh                 # Windows: setup.bat
source .venv/bin/activate

python -m arc verify                                   # ตรวจ 1,120 task
python -m arc eval --solver composite --split training # วัดคะแนน
python -m arc show 007bbfb7                            # ดู task เป็นภาพ
pytest
```

## ข้อจำกัดที่ต้องรู้ก่อนเขียนโค้ด ARC-AGI-3

1. **Internet ปิดระหว่าง scoring** → solver ที่เรียก LLM API ภายนอก **ส่งไม่ได้**
2. **Python 3.12 บังคับ** (ส่วน `arc2/` ใช้ 3.11 ได้ แต่ `agi3/` ต้อง 3.12)
3. **ต้อง open source แบบ CC0 หรือ MIT-0** — repo นี้ใช้ **MIT-0** (ดู `LICENSE`) — **MIT-0 ≠ MIT**
4. **ผู้เข้าแข่งที่เป็นผู้เยาว์** — เกณฑ์อายุของไทยคือ **20 ปี ไม่ใช่ 18** และต้องได้
   **ทั้ง Sponsor agreement และ guardian consent ก่อน entry deadline** ไม่ใช่ตอนชนะ
   → [`docs/eligibility-minor.md`](docs/eligibility-minor.md) มี checklist และร่างอีเมลพร้อมส่ง

ที่มาของทุกข้อพร้อม URL: [`docs/competition-brief.md`](docs/competition-brief.md)
(เป็นงานค้นคว้าอัตโนมัติ — ข้อ 1 กับ 4 ควรยืนยันกับหน้ากติกา Kaggle ด้วยตัวเองก่อนพึ่งพา)

## กติกาการทำงาน

> **ห้ามมโนตัวเลข — ทุกตัวเลขต้องวัดจริงและย้อนกลับไปหาที่มาได้**

`python -m arc eval` พิมพ์ commit hash และ timestamp กำกับทุกการรัน ตัวเลขที่จะเขียนลง
writeup ต้องมาจาก run จริงเท่านั้น และห้าม tune บนชุด evaluation ซ้ำ ๆ แล้วรายงานคะแนนนั้น

## ที่มา

แยกออกมาจาก repo `Panus15/EcosyncAi` เมื่อ 11 ก.ย. 2026 เพราะ ARC Prize บังคับ
open source แบบ CC0/MIT-0 ซึ่งขัดกับสัญญาอนุญาตเชิงพาณิชย์ของโครงงาน EcoSync
เป็นคนละโครงงานกัน ประวัติ commit ช่วงแรกอยู่ที่ repo เดิม
