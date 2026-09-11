# ARC Prize 2026

การเข้าแข่ง **ARC Prize 2026** — agent สำหรับ **ARC-AGI-3** และ writeup สำหรับ **Paper Track**
พร้อมเส้นฐานที่วัดจริงบน **ARC-AGI-2**

> **ปิดรับ 10 พ.ย. 2026 · 06:59 GMT+7**
> ⚠️ **Milestone #2: 30 ก.ย. 2026** — ต้อง open source ภายในวันนั้น

## สถานะ

| ส่วน | สถานะ |
|---|---|
| ARC-AGI-2 loader + evaluation harness | ✅ เสร็จ — 122 เทสผ่าน |
| ARC-AGI-2 rule baselines (14 ตัว) | ✅ วัดจริงแล้ว — ดู `docs/baselines.md` |
| สถิติชุดข้อมูล | ✅ `docs/dataset-analysis.md` |
| สืบกติกาการแข่ง | ✅ `docs/competition-brief.md` |
| **ARC-AGI-3 agent** | ⬜ ยังไม่เริ่ม → `agi3/` |
| **Paper Track writeup** | ⬜ ยังไม่เริ่ม |

## ผลที่วัดได้แล้ว

rule-based solver ทั้ง 14 ตัวได้ **0.00% บนชุด evaluation ของ ARC-AGI-2** (0 จาก 120 ข้อ)
ขณะที่ composite ได้ **7.70% บน training** (77 จาก 1000)

ผลวินิจฉัยที่สำคัญกว่า: บน training กฎที่ fit ได้ตอบถูก **77/77 (100%)** แต่บน evaluation
**ไม่มีกฎไหน fit ได้แม้แต่ข้อเดียว** — กฎไม่ได้ตอบผิด แต่ใช้ไม่ได้เลย
แปลว่าการเพิ่มกฎแบบเดิมจะยังได้ 0% ต้องเปลี่ยนประเภทวิธี ไม่ใช่เพิ่มปริมาณ

รายละเอียดและวิธีทำซ้ำ: [`docs/baselines.md`](docs/baselines.md)

## โครงสร้าง

```
arc-prize-2026/
├── docs/
│   ├── ROADMAP.md            แผนงาน + กำหนดการ + ข้อจำกัดที่ต้องออกแบบรอบ
│   ├── competition-brief.md  กติกาทั้ง 3 สนาม พร้อมแหล่งอ้างอิงรายข้อ
│   ├── baselines.md          ผลวัด baseline จริง
│   └── dataset-analysis.md   สถิติ ARC-AGI-2 ทั้ง 1,120 task
├── arc2/                     งาน ARC-AGI-2 (loader, harness, solvers, tests)
└── agi3/                     ARC-AGI-3 agent — สนามหลัก
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
4. **ผู้เข้าแข่งที่เป็นผู้เยาว์** ต้องมี parental/guardian consent และถ้าชนะ ผู้ปกครองต้องลงนามภายใน 7 วัน

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
