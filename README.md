# ARC Prize 2026 — what a program-only agent can establish about an unknown environment

An entry to **ARC Prize 2026**: an agent for **ARC-AGI-3** and a **Paper Track** writeup,
with measured baselines on ARC-AGI-2. No neural network, no GPU. MIT-0.

The contribution is not the agent but what building it showed: **five times, a method
that convinced us in a simulator failed against real data**, and each time it was caught
only by testing against data we had not generated. The writeup is about the mechanisms.

## The main result

The same policies in two arenas — the quiet environment we wrote first, and the same
environment carrying noise measured from 500 recorded real runs:

```
policy       learns?      quiet mock    noise-calibrated mock
-------------------------------------------------------------
random            no     lost 2/3            lost 2/3
greedy            no      WIN 3/3             WIN 3/3
explorer         yes      WIN 3/3            lost 0/3
navigator        yes      WIN 3/3            lost 0/3
```

Noise destroys only the methods that learn; on a board carrying the noise real boards
carry, random play beats both deliberate policies. The arena they fail in was itself
calibrated from real runs — matching measured statistics is not enough to make a
simulator trustworthy.

## Where to look

| | |
|---|---|
| the writeup | [`paper/writeup-draft.md`](paper/writeup-draft.md) · cover [`paper/cover.png`](paper/cover.png) |
| the public notebook — runs offline, recomputes the simulation tables | [`paper/notebook.ipynb`](paper/notebook.ipynb) |
| **every figure in the writeup → the command that reproduces it** | [`docs/EVIDENCE.md`](docs/EVIDENCE.md) |
| agents frozen before any real game was seen | [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md) |
| the Kaggle submission notebook (ARC-AGI-3) | [`agi3/submission/kaggle/submission.ipynb`](agi3/submission/kaggle/submission.ipynb) |
| the agent | [`agi3/arcagi3/`](agi3/arcagi3) — `router.py` → `navigator.py` (walking) / `clicker.py` (clicking) |
| the noise wrapper, for testing any agent | [`agi3/arcagi3/noise.py`](agi3/arcagi3/noise.py) |

## Verify it

```bash
git clone https://github.com/Panus15/arc-prize-2026 && cd arc-prize-2026
(cd agi3 && ./setup.sh)          # Python 3.12, as the competition SDK requires
./check.sh                        # lint, tests, word budget, every writeup figure traced, no secrets
cd agi3 && PYTHONPATH=. .venv/bin/python scripts/simulation_gap.py --skip-traces   # the table above
```

Figures measured on the recorded real runs need those runs
(`git clone https://github.com/Tufalabs/duck-harness`); [`docs/EVIDENCE.md`](docs/EVIDENCE.md)
gives the command for each.

## Layout

```
agi3/     ARC-AGI-3: the agent, mock environments, scripts that reproduce every figure,
          tests, and the Kaggle submission (submission/)
paper/    the writeup, its notebook and cover, their builders, and the word/figure checks
docs/     working notes, one per measurement (in Thai), indexed in English by EVIDENCE.md
arc2/     ARC-AGI-2 loader, evaluation harness and 14 rule baselines (0.00% on evaluation)
```

---

## ภาษาไทย — สำหรับเจ้าของโครงการ

> **ปิดรับ 10 พ.ย. 2026 · 06:59 GMT+7**

| ส่วน | สถานะ |
|---|---|
| ARC-AGI-2 loader + harness + baselines 14 ตัว | ✅ วัดจริงแล้ว — `docs/baselines.md` |
| **ARC-AGI-3 agent** | ✅ **254 เทสผ่าน** · เล่นกระดานจริง 500 รอบไม่พังเลย → `agi3/` |
| **Paper Track writeup** | 🟡 ครบทุกหัวข้อ · §1 ปิดท้าย + §8 รอผลเกมจริง · ตัวเลขทุกตัวมีที่มา (`./check.sh`) |
| **cover image + public notebook** | ✅ `paper/cover.png` · `paper/notebook.ipynb` (ฝังโค้ดในตัว รันบน Kaggle ได้) |
| **Kaggle submission (ARC-AGI-3)** | 🟡 notebook พร้อมอัปโหลด · จำลอง Kaggle ครบ 2 รอบผ่าน · **ยังไม่ได้ submit** |
| **เกมจริง** | ⛔ ยังไม่เคยรัน — ต้องดาวน์โหลดไฟล์เกมครั้งเดียวจากเครื่องที่ต่อ `arcprize.org` ได้ |
| **สิทธิ์เข้าแข่ง (ผู้เยาว์)** | ⛔ ต้องถาม Sponsor · ร่างอีเมลพร้อมส่งที่ [`docs/eligibility-minor.md`](docs/eligibility-minor.md) |

**สิ่งที่ต้องทำ ทีละขั้น: [`docs/YOUR-STEPS.md`](docs/YOUR-STEPS.md)** ·
แผนงานเต็ม: [`docs/ROADMAP.md`](docs/ROADMAP.md)

### ข้อจำกัดที่ต้องรู้

1. **Internet ปิดระหว่าง scoring** → solver ที่เรียก LLM API ภายนอกส่งไม่ได้
2. **Python 3.12 บังคับ** สำหรับ `agi3/` (ส่วน `arc2/` ใช้ 3.11 ได้)
3. **ต้อง open source แบบ CC0 หรือ MIT-0** — repo นี้ใช้ **MIT-0** (`LICENSE`) — **MIT-0 ≠ MIT**
4. **ผู้เข้าแข่งที่เป็นผู้เยาว์** — เกณฑ์อายุของไทยคือ **20 ปี ไม่ใช่ 18** และต้องได้
   **ทั้ง Sponsor agreement และ guardian consent ก่อน entry deadline** →
   [`docs/eligibility-minor.md`](docs/eligibility-minor.md)

### กติกาการทำงาน

> **ห้ามมโนตัวเลข — ทุกตัวเลขต้องวัดจริงและย้อนกลับไปหาที่มาได้**
> `./check.sh` บังคับข้อนี้กับเปเปอร์โดยอัตโนมัติ

แยกออกมาจาก repo `Panus15/EcosyncAi` เมื่อ 11 ก.ย. 2026 เพราะ ARC Prize บังคับ
open source แบบ CC0/MIT-0 ซึ่งขัดกับสัญญาอนุญาตเชิงพาณิชย์ของโครงงาน EcoSync
