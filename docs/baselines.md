# Baseline solvers — ผลวัดจริง

> วัดเมื่อ **2026-09-11** · repo commit **`efca374`** · dataset commit **`f3283f7`** · Python 3.11.15
> ตัวเลขทุกตัวในหน้านี้มาจากการรัน `python -m arc eval` จริง ไม่มีตัวไหนประมาณเอา

## 1. ผลสรุป

**ทุก rule-based solver ได้ 0.00% บนชุด evaluation — ไม่มีตัวไหนแก้ได้แม้แต่ข้อเดียวจาก 120 ข้อ**

| solver | training (1000) | evaluation (120) | errors |
|---|---:|---:|---:|
| **composite** (รวมทุกกฎ) | **77 · 7.70%** | **0 · 0.00%** | 0 |
| panel_logic | 20 · 2.00% | 0 · 0.00% | 0 |
| tiling | 16 · 1.60% | 0 · 0.00% | 0 |
| crop | 7 · 0.70% | 0 · 0.00% | 0 |
| geometry | 7 · 0.70% | 0 · 0.00% | 0 |
| symmetry_repair | 6 · 0.60% | 0 · 0.00% | 0 |
| colour_map | 4 · 0.40% | 0 · 0.00% | 0 |
| downscale | 4 · 0.40% | 0 · 0.00% | 0 |
| fractal_tile | 4 · 0.40% | 0 · 0.00% | 0 |
| panel_select | 4 · 0.40% | 0 · 0.00% | 0 |
| upscale | 3 · 0.30% | 0 · 0.00% | 0 |
| shape_fill | 2 · 0.20% | 0 · 0.00% | 0 |
| constant_output | 0 · 0.00% | 0 · 0.00% | 0 |
| identity | 0 · 0.00% | 0 · 0.00% | 0 |

`errors = 0` ทุกช่อง แปลว่าไม่มี solver ตัวไหน crash หรือคืนค่าผิดรูปแบบ — เลข 0% คือ "ตอบไม่ได้" ไม่ใช่ "โค้ดพัง"

## 2. ผลวินิจฉัย: abstain หรือ ตอบผิด?

ตัวเลข 0% เพียงอย่างเดียวบอกไม่ได้ว่ากฎ *ใช้ไม่ได้เลย* หรือ *ใช้ได้แต่ generalize ผิด* จึงแยกวัดว่าแต่ละ solver "ยอมตอบ" (attempted — ผลิต candidate อย่างน้อย 1 ชิ้น) กี่ข้อ

| split | tasks ที่มีกฎใด ๆ ยอมตอบ | solved | precision เมื่อยอมตอบ |
|---|---:|---:|---:|
| training (1000) | **77** | 77 | **100.0%** |
| evaluation (120) | **0** | 0 | — |

สองบรรทัดนี้คือผลที่สำคัญที่สุดของ Phase 1:

1. **บน training — เมื่อกฎ fit ได้ มันถูกเสมอ 77/77 (100%)** วินัย *fit-then-abstain* (กฎจะตอบก็ต่อเมื่อสร้าง train output ได้ครบทุกคู่) ทำงานได้ตามออกแบบ
2. **บน evaluation — ไม่มีกฎไหน fit ได้แม้แต่ข้อเดียว** ทั้ง 120 ข้อ ไม่ใช่ว่าตอบแล้วผิด แต่คือ **ไม่มีข้อไหนอธิบายได้ด้วยการแปลงพื้นฐาน 14 แบบนี้เลย**

> ⚠️ ข้อควรระวังในการตีความ: precision 100% ส่วนหนึ่งเป็นผลจากการออกแบบ (บังคับให้ abstain เมื่อ fit ไม่ได้) และฐานมีแค่ 77 ข้อ จึงไม่ควรอ้างว่า "กฎที่ fit ได้จะถูกเสมอ" เป็นกฎทั่วไป — ที่พูดได้คือ บนชุด training นี้ ไม่มีกรณี fit-แล้ว-ผิด เกิดขึ้นเลย

## 3. ตีความ

ชุด evaluation ของ ARC-AGI-2 ถูกคัดมาให้ **ไม่มีความสม่ำเสมอตื้น ๆ (shallow regularity) เหลืออยู่เลย** ขณะที่ชุด training ยังมีอยู่ 7.7%

ผลต่อการออกแบบวิธี:
- **การเพิ่มกฎแบบเดิมไม่ช่วย** — ไม่ใช่ว่ากฎยังไม่พอ แต่ประเภทของกฎนี้ผิดประเภทสำหรับ evaluation การไล่เพิ่ม rule ตัวที่ 15, 16, 17 คาดว่าจะยังได้ 0%
- **ต้องใช้วิธีที่ประกอบกฎเข้าด้วยกันได้** (compositional) ไม่ใช่จับคู่ template ตัวเดียว
- **7.7% บน training คือเพดานของ approach นี้** ใช้เป็นเส้นฐานเทียบว่าวิธีใหม่เก่งขึ้นจริงหรือแค่ทำสิ่งเดิม
- ตัวเลขนี้ทำให้ข้ออ้างใด ๆ ในเปเปอร์ว่า "วิธีเราดีกว่า baseline" มีความหมาย เพราะ baseline วัดจริงแล้ว ไม่ใช่อ้างลอย ๆ

## 4. กฎที่ implement ไว้ (14 ตัว)

| solver | กฎ |
|---|---|
| identity | output = input |
| constant_output | ทุก train output เหมือนกัน → ตอบตัวนั้น |
| geometry | หมุน 90/180/270, พลิกแนวนอน/ตั้ง, transpose, anti-transpose |
| tiling | output = input ปูซ้ำ k×m (รวมแบบสลับกระจก) |
| fractal_tile | ปูซ้ำแบบ fractal ตามค่าในเซลล์ |
| upscale / downscale | ขยายเซลล์เป็นบล็อก k×m / ย่อกลับ |
| colour_map | รูปทรงเดิม เปลี่ยนเฉพาะสีแบบ 1-ต่อ-1 |
| crop | output = สี่เหลี่ยมย่อยของ input (bounding box ของเนื้อหา) |
| symmetry_repair | เติมส่วนที่ถูกบัง โดยใช้สมมาตรของ grid |
| panel_select | input แบ่งเป็นหลาย panel → เลือก panel เดียวตามเกณฑ์ |
| panel_logic | สอง panel รวมกันด้วย AND/OR/XOR/NOR/… |
| shape_fill | เติมสีทึบตามรูปทรงที่เรียนจาก train |
| composite | รันทุกกฎ เก็บ candidate จากกฎที่ fit แล้วตอบไม่เกิน 2 ชิ้น |

ทุกตัวใช้วินัยเดียวกัน: **fit บน `task.train` ก่อน ถ้าสร้าง output ครบทุกคู่ไม่ได้ → abstain** (คืน `[]`)
วินัยนี้มีเทสคุมอยู่ใน `tests/test_solvers.py` และ parametrize ครอบ solver ทุกตัวที่ลงทะเบียน กฎใหม่ที่เพิ่มเข้ามาจะถูกบังคับอัตโนมัติ

## 5. ทำซ้ำผลนี้

```bash
cd arc2
./setup.sh                      # ถ้ายังไม่มี .venv / dataset
source .venv/bin/activate

# ตารางข้อ 1 — ทีละ solver
python -m arc eval --solver composite --split evaluation
python -m arc eval --solver composite --split training --quiet

# เก็บผลเต็มพร้อม provenance ลงไฟล์
python -m arc eval --solver composite --split evaluation --json runs/composite-eval.json

# รายชื่อ solver ทั้งหมด
python -c "from arc.solver import available_solvers; print(available_solvers())"
```

ผลลัพธ์ทุกครั้งพิมพ์ `commit` และ `run` (timestamp UTC) กำกับ — ตัวเลขในเปเปอร์ต้องย้อนกลับไปหา run ที่ผลิตมันได้เสมอ

ตัวอย่างผลจริงของคำสั่งแรก:

```
solver     composite
split      evaluation
commit     efca374
run        2026-09-11T15:49:07+00:00
solved     0/120  (0.00%)
time       0.52s total, 0.004s/task
errors     0
```

## 6. ยังไม่ได้ทำ

- ยังไม่ได้แยกว่า 77 ข้อที่แก้ได้บน training เป็นข้อประเภทไหน (จับคู่กับ taxonomy ใน `dataset-analysis.md` ได้)
- ยังไม่ได้วัดว่ากฎไหน "เกือบ fit" บน evaluation (เช่น สร้าง train output ได้ 2 จาก 3 คู่) ซึ่งจะบอกว่าห่างจากการใช้ได้แค่ไหน
