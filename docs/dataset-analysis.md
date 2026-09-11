# โปรไฟล์สถิติของ ARC-AGI-2 public corpus

> วัดจริงทั้งหมด ไม่มีตัวเลขประมาณ — ทุกตารางในเอกสารนี้พิมพ์ออกมาจาก
> `arc2/scripts/analyze_tasks.py` โดยตรง

## Provenance

| รายการ | ค่า |
|---|---|
| วันที่วัด | 2026-09-10 |
| `git rev-parse --short HEAD` (workspace) | `e047564` |
| `git rev-parse --short HEAD` (ARC-AGI-2 checkout) | `f3283f7` (2025-05-15, "readme updates") |
| dataset path | `arc2/ARC-AGI-2/data` |
| Python | 3.11.15 · numpy 2.4.6 |
| เวลาที่ใช้รันเต็มคลัง | ~3.4 วินาที |

คำสั่งที่สร้าง **ทุกตาราง** ในเอกสารนี้ (รันจาก `arc2/`):

```bash
.venv/bin/python scripts/analyze_tasks.py --json profile.json
```

รายงานที่พิมพ์ออกมาแบ่งเป็นหัวข้อ `-- 1. ... -- 7. ...` ต่อ split; แต่ละตาราง
ข้างล่างจะบอกไว้ว่าอ่านจากหัวข้อไหน ถ้าต้องการเฉพาะ split เดียวใช้
`--split training` หรือ `--split evaluation` (หัวข้อ 7 จะปรากฏก็ต่อเมื่อรันทั้งสอง
split พร้อมกัน) ผลลัพธ์ deterministic — รันสองครั้งได้ไฟล์ md5 เดียวกัน

## 0. นิยามที่ใช้วัด (สำคัญต่อการอ่านตัวเลข)

ARC ไม่ได้ประกาศ background หรือ "object" ไว้ในไฟล์ task ตัวเลขทุกตัวจึงขึ้นกับนิยาม
ที่เลือก และนี่คือนิยามที่สคริปต์ใช้:

| คำ | นิยามที่ compute จริง |
|---|---|
| background ของ grid | symbol ที่พบบ่อยที่สุดใน grid นั้น (modal symbol) เสมอกันให้เลือก symbol id ต่ำสุด |
| background ของ task | symbol ที่พบบ่อยที่สุดเมื่อรวมทุก grid (input+output, train+test) ของ task |
| object / connected component | บริเวณ 4-connectivity ที่เป็น **สีเดียวกัน** โดยถือ background เป็นช่องว่าง |
| identical shape | `input_shape == output_shape` |
| output is an integer multiple | `out_h % in_h == 0 and out_w % in_w == 0` (ไม่นับกรณี 1×1 ซึ่งคือ identical) |
| input is an integer multiple | สลับด้านของข้อบน |
| fixed output shape | ทุก pair ใน task เดียวกันมี output shape เท่ากันหมด |
| tiling | output = input ซ้ำ k×m ครั้ง โดย **ทุก tile เหมือน input เป๊ะ** |
| tile_d4 | เงื่อนไขหลวมกว่า: แต่ละ tile เป็น dihedral image ตัวใดตัวหนึ่งของ input |
| upscale | ทุกเซลล์ของ input ขยายเป็นบล็อก k×m (nearest-neighbour) |
| crop | output เท่ากับ sub-rectangle ต่อเนื่องของ input และเล็กกว่า input |
| D4 | กลุ่ม 8 การแปลงแข็ง: identity, rot90/180/270, flip_lr, flip_ud, transpose, anti-transpose |
| quartile | `numpy.percentile` แบบ linear interpolation |
| CI95 | Wilson score interval (closed form ไม่มีการสุ่ม ไม่มี bootstrap) |

**ข้อควรระวังเรื่อง CI**: interval ระดับ pair/grid *แคบเกินจริง* เพราะ grid ภายใน task
เดียวกันไม่เป็นอิสระต่อกัน ตัวเลขที่เชื่อได้มากที่สุดสำหรับการเทียบ split คือ
สัดส่วนระดับ **task** (n = 1000 กับ n = 120)

## 1. ขนาดของคลัง

จากบรรทัดหัวเรื่องของแต่ละ split

| split | tasks | pairs | grids | pairs ที่มี output |
|---|---|---|---|---|
| training | 1000 | 4308 | 8616 | 4308 |
| evaluation | 120 | 526 | 1052 | 526 |

public split มี output ครบทุก pair (รวม test) จึงวัดความสัมพันธ์ input→output ได้ทุกคู่

## 2. ความสัมพันธ์ของรูปทรง input/output

หัวข้อ `-- 1. shape relations --`

ระดับ pair (ตัวส่วน = pairs ที่มี output):

| relation | training | % | evaluation | % |
|---|---|---|---|---|
| identical shape | 2837 / 4308 | 65.85% | 367 / 526 | 69.77% |
| output is an integer multiple | 302 / 4308 | 7.01% | 3 / 526 | 0.57% |
| input is an integer multiple | 279 / 4308 | 6.48% | 11 / 526 | 2.09% |
| none of the above | 890 / 4308 | 20.66% | 145 / 526 | 27.57% |

ระดับ task:

| คุณสมบัติ | training | % | evaluation | % |
|---|---|---|---|---|
| ทุก pair คงรูปทรงเดิม | 680 / 1000 | 68.00% | 81 / 120 | 67.50% |
| output shape เท่ากันหมดใน task | 413 / 1000 | 41.30% | 25 / 120 | 20.83% |
| ↳ ในจำนวนนั้น input shape ไม่คงที่ | 34 / 1000 | 3.40% | 1 / 120 | 0.83% |
| อัตราส่วนขนาดคงที่ (ไม่ใช่ 1:1) | 140 / 1000 | 14.00% | 2 / 120 | 1.67% |

บรรทัดที่ 3 คือประเด็นสำคัญ: "fixed output shape" ส่วนใหญ่เกิดเพราะ **input ก็ขนาดคงที่
อยู่แล้ว** เคสที่ output shape คงที่ทั้งที่ input เปลี่ยนขนาด (ซึ่งเป็นเคสเดียวที่
"จำขนาด output ไว้" มีประโยชน์จริง) มีแค่ 34 task ใน training และ 1 task ใน evaluation

## 3. การกระจายขนาด grid

หัวข้อ `-- 1b + 5. grid size, palette size and object counts --`

### training (4308 input grids / 4308 output grids)

| ค่า | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|
| input height | 1 | 7.0 | 10.0 | 16.0 | 30 | 11.85 |
| input width | 1 | 8.0 | 11.0 | 16.0 | 30 | 12.39 |
| input cells | 2 | 51.0 | 100.0 | 255.0 | 900 | 184.66 |
| output height | 1 | 5.0 | 10.0 | 14.0 | 30 | 10.42 |
| output width | 1 | 6.0 | 10.0 | 15.0 | 30 | 10.87 |
| output cells | 1 | 28.0 | 100.0 | 208.0 | 900 | 150.46 |

### evaluation (526 input grids / 526 output grids)

| ค่า | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|
| input height | 4 | 12.0 | 19.0 | 24.0 | 30 | 18.71 |
| input width | 3 | 15.0 | 20.0 | 25.0 | 30 | 19.44 |
| input cells | 16 | 170.5 | 361.0 | 575.8 | 900 | 401.24 |
| output height | 2 | 10.0 | 16.0 | 22.0 | 30 | 16.72 |
| output width | 1 | 11.0 | 17.0 | 22.0 | 30 | 16.95 |
| output cells | 10 | 121.0 | 256.0 | 482.2 | 900 | 322.89 |

evaluation ไม่มี grid จิ๋วเลย: input เล็กสุด 16 เซลล์ ขณะที่ training มี input 2 เซลล์
และ output 1 เซลล์

## 4. การใช้สี

หัวข้อ `-- 2. colour usage --`

### palette size

| ค่า | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|
| ต่อ input grid — training | 1 | 2.0 | 3.0 | 5.0 | 10 | 3.90 |
| ต่อ input grid — evaluation | 2 | 4.0 | 5.0 | 7.0 | 10 | 5.48 |
| ต่อ output grid — training | 1 | 3.0 | 3.0 | 4.0 | 10 | 3.70 |
| ต่อ output grid — evaluation | 2 | 3.0 | 5.0 | 6.0 | 10 | 4.89 |
| ต่อ task — training | 2 | 4.0 | 6.0 | 8.0 | 10 | 6.26 |
| ต่อ task — evaluation | 2 | 6.8 | 8.5 | 10.0 | 10 | 7.90 |

การแจกแจง palette ต่อ task (จำนวน task ต่อขนาด palette):

| palette | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| training | 21 | 145 | 121 | 98 | 149 | 132 | 124 | 96 | 114 |
| evaluation | 1 | 5 | 4 | 8 | 12 | 15 | 15 | 22 | 38 |

evaluation ใช้ palette เต็ม 10 สีถึง 38/120 task (31.67% — คำนวณจากตารางนี้)

### สีไหนทำหน้าที่ background

จำนวน input grid แยกตาม modal symbol:

| symbol | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| training | 2878 | 192 | 137 | 109 | 123 | 113 | 62 | 384 | 266 | 44 |
| evaluation | 180 | 59 | 19 | 30 | 39 | 7 | 18 | 50 | 114 | 10 |

จำนวน task แยกตาม modal symbol ของทั้ง task:

| symbol | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| training | 702 | 36 | 31 | 14 | 25 | 21 | 12 | 93 | 61 | 5 |
| evaluation | 39 | 14 | 3 | 8 | 14 | 1 | 5 | 9 | 26 | 1 |

| measure | training | % | evaluation | % |
|---|---|---|---|---|
| input grid ที่ background ≠ 0 | 1430 / 4308 | 33.19% | 346 / 526 | 65.78% |
| output grid ที่ background ≠ 0 | 1878 / 4308 | 43.59% | 381 / 526 | 72.43% |
| task ที่ background ≠ 0 | 298 / 1000 | 29.80% | 81 / 120 | 67.50% |
| input grid ที่ **ไม่มี symbol 0 อยู่เลย** | 916 / 4308 | 21.26% | 258 / 526 | 49.05% |

### output palette เทียบกับ input palette

| measure | training | % | evaluation | % |
|---|---|---|---|---|
| output palette ⊆ input palette | 3008 / 4308 | 69.82% | 462 / 526 | 87.83% |
| output palette = input palette | 1995 / 4308 | 46.31% | 283 / 526 | 53.80% |
| output มีสีใหม่ที่ไม่มีใน input | 1300 / 4308 | 30.18% | 64 / 526 | 12.17% |
| output ทิ้งสีที่ input มี | 1479 / 4308 | 34.33% | 193 / 526 | 36.69% |

จำนวนสีใหม่ต่อ pair (จำนวน pair):

| สีใหม่ | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| training | 3008 | 978 | 207 | 64 | 33 | 10 | 3 | 1 | 4 |
| evaluation | 462 | 49 | 10 | 4 | 1 | 0 | 0 | 0 | 0 |

สีที่ถูก "แต่งเติมเข้ามา" บ่อยที่สุด (นับเป็นจำนวน pair ต่อ symbol):

| symbol | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| training | 75 | 267 | 375 | 292 | 218 | 128 | 105 | 76 | 243 | 44 |
| evaluation | 8 | 4 | 11 | 15 | 3 | 8 | 8 | 10 | 11 | 7 |

## 5. ความสัมพันธ์ trivial — เพดานที่แท้จริงของ baseline

หัวข้อ `-- 3. trivial relations --`

ระดับ pair:

| relation | training | % | evaluation | % |
|---|---|---|---|---|
| identity (output = input เป๊ะ) | 10 / 4308 | 0.23% | 1 / 526 | 0.19% |
| rot90 | 8 / 4308 | 0.19% | 0 / 526 | 0.00% |
| rot180 | 14 / 4308 | 0.32% | 0 / 526 | 0.00% |
| rot270 | 4 / 4308 | 0.09% | 0 / 526 | 0.00% |
| flip_lr | 11 / 4308 | 0.26% | 0 / 526 | 0.00% |
| flip_ud | 10 / 4308 | 0.23% | 0 / 526 | 0.00% |
| transpose | 12 / 4308 | 0.28% | 0 / 526 | 0.00% |
| anti_transpose | 3 / 4308 | 0.07% | 0 / 526 | 0.00% |
| tiling (ทุก tile = input) | 22 / 4308 | 0.51% | 0 / 526 | 0.00% |
| tile_d4 (tile เป็น D4 image) | 109 / 4308 | 2.53% | 0 / 526 | 0.00% |
| upscale | 27 / 4308 | 0.63% | 0 / 526 | 0.00% |
| downscale | 2 / 4308 | 0.05% | 0 / 526 | 0.00% |
| crop (มี sub-rectangle ที่ตรง) | 254 / 4308 | 5.90% | 1 / 526 | 0.19% |
| **ANY ของ identity/D4/tiling/upscale** | **94 / 4308** | **2.18%** | **1 / 526** | **0.19%** |

ระดับ task — กฎเดียวต้องใช้ได้กับ **ทุก pair** ของ task (และถ้าเป็นกฎขยาย/ย่อ ต้องใช้
factor เดียวกันทุก pair เพราะ solver ต้องอนุมาน factor จาก demonstration):

| กฎ | training | % | evaluation | % |
|---|---|---|---|---|
| identity | 0 / 1000 | 0.00% | 0 / 120 | 0.00% |
| rot90 | 1 / 1000 | 0.10% | 0 / 120 | 0.00% |
| rot180 | 2 / 1000 | 0.20% | 0 / 120 | 0.00% |
| rot270 | 0 / 1000 | 0.00% | 0 / 120 | 0.00% |
| flip_lr | 1 / 1000 | 0.10% | 0 / 120 | 0.00% |
| flip_ud | 1 / 1000 | 0.10% | 0 / 120 | 0.00% |
| transpose | 2 / 1000 | 0.20% | 0 / 120 | 0.00% |
| anti_transpose | 0 / 1000 | 0.00% | 0 / 120 | 0.00% |
| tiling | 1 / 1000 | 0.10% | 0 / 120 | 0.00% |
| upscale | 3 / 1000 | 0.30% | 0 / 120 | 0.00% |
| downscale | 0 / 1000 | 0.00% | 0 / 120 | 0.00% |
| crop | 51 / 1000 | 5.10% | 0 / 120 | 0.00% |
| **ANY กฎ trivial เดียว (ไม่นับ crop)** | **11 / 1000** | **1.10%** | **0 / 120** | **0.00%** |
| output ทุกอันเหมือนกันหมด (constant output) | 0 / 1000 | 0.00% | 0 / 120 | 0.00% |

หมายเหตุสองข้อ:

1. **crop ไม่ใช่โปรแกรม** — มันบอกแค่ว่า "มี sub-rectangle ที่ตรง" ไม่ได้บอกว่า
   ต้องตัดตรงไหน จึงแยกออกจากตัวเลข ANY เพดานจริงของ trivial baseline คือ
   **11/1000 (1.10%)** ใน training และ **0/120 (0.00%, CI95 [0.00, 3.10])** ใน evaluation
2. ตัวเลข ANY ระดับ pair (94) น้อยกว่าผลรวมของแต่ละแถว เพราะ grid ที่สมมาตรเข้าเงื่อนไข
   หลายกฎพร้อมกัน
3. pair ที่ output มีไม่เกิน 4 เซลล์: training 131 / 4308 (3.04%), evaluation 0 / 526 (0.00%)
   — เคส crop จิ๋ว ๆ ที่ทำให้ตัวเลข crop ของ training ดูสูง ไม่มีใน evaluation เลย

## 6. Symmetry ของ grid

หัวข้อ `-- 4. symmetry --` (`transpose` นับเฉพาะ grid จัตุรัส ตัวส่วนจึงต่างจากแถวอื่น)

| measure | training | % | evaluation | % |
|---|---|---|---|---|
| input: square | 2613 / 4308 | 60.65% | 317 / 526 | 60.27% |
| input: flip_lr symmetric | 237 / 4308 | 5.50% | 8 / 526 | 1.52% |
| input: flip_ud symmetric | 213 / 4308 | 4.94% | 9 / 526 | 1.71% |
| input: rot180 symmetric | 148 / 4308 | 3.44% | 5 / 526 | 0.95% |
| input: transpose symmetric (ต่อ grid จัตุรัส) | 223 / 2613 | 8.53% | 7 / 317 | 2.21% |
| **input: สมมาตรอย่างน้อยหนึ่งแบบ** | **528 / 4308** | **12.26%** | **24 / 526** | **4.56%** |
| output: square | 2736 / 4308 | 63.51% | 290 / 526 | 55.13% |
| output: flip_lr symmetric | 581 / 4308 | 13.49% | 41 / 526 | 7.79% |
| output: flip_ud symmetric | 474 / 4308 | 11.00% | 37 / 526 | 7.03% |
| output: rot180 symmetric | 420 / 4308 | 9.75% | 26 / 526 | 4.94% |
| output: transpose symmetric (ต่อ grid จัตุรัส) | 426 / 2736 | 15.57% | 22 / 290 | 7.59% |
| **output: สมมาตรอย่างน้อยหนึ่งแบบ** | **988 / 4308** | **22.93%** | **71 / 526** | **13.50%** |

ทั้งสอง split output สมมาตรบ่อยกว่า input เกือบเท่าตัว — สอดคล้องกับที่ task จำนวนหนึ่ง
มีเป้าหมายเป็นการ "ซ่อม/สร้างความสมมาตร"

## 7. โครงสร้าง object (connected components, 4-connectivity)

หัวข้อ `-- 1b + 5. --` บรรทัด `objects`

| ชุด | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|
| training input (background = modal) | 0 | 3.0 | 6.0 | 11.0 | 586 | 14.70 |
| training output (background = modal) | 0 | 3.0 | 6.0 | 12.0 | 626 | 13.24 |
| evaluation input (background = modal) | 1 | 7.0 | 12.0 | 20.8 | 461 | 27.23 |
| evaluation output (background = modal) | 1 | 5.0 | 10.0 | 22.0 | 411 | 22.09 |

ถ้าบังคับให้ background = symbol 0 (แทนที่จะใช้ modal) จำนวน component จะเพิ่มขึ้น:

| ชุด | min | q1 | median | q3 | max | mean |
|---|---|---|---|---|---|---|
| training input (background = 0) | 0 | 3.0 | 6.0 | 12.0 | 782 | 15.33 |
| training output (background = 0) | 0 | 3.0 | 6.0 | 13.0 | 841 | 14.12 |
| evaluation input (background = 0) | 1 | 8.0 | 13.0 | 22.0 | 558 | 30.70 |
| evaluation output (background = 0) | 1 | 7.0 | 12.0 | 24.0 | 508 | 24.93 |

ส่วนต่าง mean ของ evaluation input (27.23 → 30.70) คือราคาที่จ่ายเมื่อสมมติ background
ผิด — วัดจากคลังจริง ไม่ใช่การประมาณ

## 8. รูปร่างของ task

หัวข้อ `-- 6. task shape --`

จำนวน train pair ต่อ task:

| train pairs | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 10 |
|---|---|---|---|---|---|---|---|---|
| training | 158 | 575 | 189 | 49 | 18 | 8 | 2 | 1 |
| evaluation | 34 | 61 | 18 | 6 | 1 | 0 | 0 | 0 |

จำนวน test input ต่อ task:

| test inputs | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| training | 931 | 63 | 5 | 1 |
| evaluation | 75 | 43 | 2 | 0 |

| measure | training | evaluation |
|---|---|---|
| train pairs — min/median/max | 2 / 3.0 / 10 | 2 / 3.0 / 6 |
| train pairs — mean | 3.232 | 2.992 |
| test inputs — mean | 1.076 | 1.392 |
| task ที่ต้องตอบถูก >1 output | 69 / 1000 (6.90%) | 45 / 120 (37.50%) |

## 9. training vs evaluation — อะไรต่างจริง อะไรไม่ต่าง

หัวข้อ `-- 7. training vs evaluation --` (ต้องรันทั้งสอง split)

`CI95 overlap = yes` หมายความว่า Wilson interval ของสอง split ทับกัน → ด้วยกลุ่มตัวอย่าง
120 task **แยกไม่ออกจาก sampling noise** ไม่ใช่หลักฐานว่า "เหมือนกัน" แต่แปลว่า
"ข้อมูลเท่าที่มีไม่พอจะบอกว่าต่าง"

### ต่างชัดเจน (interval ไม่ทับกัน + effect size ใหญ่)

| measure | unit | training | evaluation | diff (pp) |
|---|---|---|---|---|
| tasks background ≠ symbol 0 | task | 29.80% | 67.50% | +37.70 |
| input grids background ≠ 0 | grid | 33.19% | 65.78% | +32.59 |
| tasks ที่มี test input มากกว่า 1 | task | 6.90% | 37.50% | +30.60 |
| tasks fixed output shape | task | 41.30% | 20.83% | −20.47 |
| pairs output palette ⊆ input | pair | 69.82% | 87.83% | +18.01 |
| pairs output มีสีใหม่ | pair | 30.18% | 12.17% | −18.01 |
| output grids สมมาตรอย่างน้อยหนึ่งแบบ | grid | 22.93% | 13.50% | −9.43 |
| input grids สมมาตรอย่างน้อยหนึ่งแบบ | grid | 12.26% | 4.56% | −7.70 |
| pairs shape relation = "none of the above" | pair | 20.66% | 27.57% | +6.91 |
| pairs output เป็นพหุคูณของ input | pair | 7.01% | 0.57% | −6.44 |
| pairs input เป็นพหุคูณของ output | pair | 6.48% | 2.09% | −4.39 |
| pairs มีความสัมพันธ์ trivial ใด ๆ | pair | 2.18% | 0.19% | −1.99 |

ค่าที่ไม่ใช่สัดส่วน (เทียบตรง ๆ ได้ ไม่มี CI):

| measure | training | evaluation | diff | อัตราส่วน |
|---|---|---|---|---|
| median input cells | 100.000 | 361.000 | +261.000 | 3.61× |
| mean input cells | 184.657 | 401.243 | +216.586 | 2.17× |
| median output cells | 100.000 | 256.000 | +156.000 | 2.56× |
| median input palette size | 3.000 | 5.000 | +2.000 | — |
| mean input palette size | 3.903 | 5.477 | +1.574 | — |
| mean task palette size | 6.265 | 7.900 | +1.635 | — |
| median objects per input grid | 6.000 | 12.000 | +6.000 | 2.00× |
| mean objects per input grid | 14.704 | 27.230 | +12.526 | 1.85× |
| mean objects per output grid | 13.237 | 22.087 | +8.850 | 1.67× |
| mean train pairs per task | 3.232 | 2.992 | −0.240 | — |
| mean test inputs per task | 1.076 | 1.392 | +0.316 | — |

(คอลัมน์ "อัตราส่วน" คำนวณจากสองคอลัมน์ซ้ายในตารางเดียวกัน)

### ยังบอกไม่ได้ว่าต่าง (CI ทับกัน — n = 120 เล็กเกินไป)

| measure | unit | training | evaluation | diff (pp) |
|---|---|---|---|---|
| pairs input/output ขนาดเท่ากัน | pair | 65.85% | 69.77% | +3.92 |
| tasks ที่ทุก pair คงรูปทรง | task | 68.00% | 67.50% | −0.50 |
| pairs output = input (identity) | pair | 0.23% | 0.19% | −0.04 |
| tasks ที่กฎ trivial เดียวใช้ได้ทุก pair | task | 1.10% | 0.00% | −1.10 |

แถวสุดท้ายต้องอ่านอย่างระวัง: evaluation ได้ 0/120 ซึ่ง CI95 คือ [0.00%, 3.10%] —
ครอบคลุมค่า 1.10% ของ training ฉะนั้น **สรุปไม่ได้** ว่า evaluation ปลอด trivial task
มากกว่า training อย่างมีนัย ที่สรุปได้คือทั้งสอง split ต่างก็อยู่ในระดับ "ไม่กี่เปอร์เซ็นต์
หรือน้อยกว่า" เหมือนกัน

### สรุปสั้น ๆ ว่า evaluation "ยากกว่า" ในเชิงที่วัดได้อย่างไร

สิ่งที่ **วัดได้จริง** ว่าต่าง: grid ใหญ่กว่า (median 361 vs 100 เซลล์), object เยอะกว่า
(median 12 vs 6), palette กว้างกว่า (median 5 vs 3 สีต่อ input grid), background ไม่ใช่
สีดำเป็นส่วนใหญ่ (67.50% ของ task), มี test input หลายอันบ่อยกว่ามาก (37.50% ของ task),
regularity แบบ scaling/tiling/symmetry หายไปเกือบหมด, และ demonstration น้อยกว่าเล็กน้อย
(mean 2.99 vs 3.23 pair)

สิ่งที่ **ไม่ต่าง** (หรือยังบอกไม่ได้): สัดส่วนงานที่ output คงรูปทรงเดิม (~68% ทั้งคู่)
และการที่ trivial transformation แทบไม่มีประโยชน์ — ทั้งสอง split ต่ำมากพอกัน

> ข้อจำกัด: ทุกอย่างข้างบนคือสถิติเชิงพื้นผิวของ grid ไม่ได้วัด "ความยากเชิงความคิด"
> (compositionality, จำนวน rule ที่ต้องประกอบกัน) ซึ่งเป็นสิ่งที่ ARC-AGI-2 อ้างว่าเป็น
> แกนของความยาก — สคริปต์นี้ไม่ได้วัดสิ่งนั้น จึงไม่พูดถึง

## 10. สิ่งที่ตัวเลขบอกเรื่องการออกแบบวิธี

1. **Rule-based / trivial baseline ไปได้ไม่ไกล — และต้องรายงานไว้เป็น floor เท่านั้น**
   กฎ trivial เดียว (identity/D4/tiling/upscale) ใช้ได้ครบทุก pair แค่ 11/1000 task
   (1.10%) ใน training และ 0/120 (0.00%) ใน evaluation ฉะนั้น solver ตระกูลนี้มีค่าเป็น
   smoke test ของ pipeline การให้คะแนน ไม่ใช่ตัววิธี ตัวเลขนี้คือ "พื้น" ที่วิธีจริง
   ต้องชนะ และควรใส่ไว้ในเปเปอร์ในฐานะ floor ที่วัดจริง

2. **ห้าม hard-code ว่า symbol 0 คือ background** — 65.78% ของ input grid ใน evaluation
   มี modal symbol ≠ 0 และ 49.05% ไม่มี symbol 0 อยู่ในภาพเลย โค้ดที่ถือว่า 0 = ว่าง
   จะแบ่ง object ผิดในราวครึ่งหนึ่งของ evaluation (mean component 27.23 → 30.70)
   ขั้นตอนอนุมาน background ต้องเป็นส่วนหนึ่งของวิธี ไม่ใช่ค่าคงที่

3. **การทำนายขนาด output ต้องมาจากเนื้อหา ไม่ใช่จากอัตราส่วน** — ใน evaluation มี pair
   ที่ output เป็นพหุคูณของ input แค่ 0.57% และ task ที่อัตราส่วนขนาดคงที่แค่ 2/120
   ขณะที่ 27.57% ของ pair ตกในกลุ่ม "none of the above" prior ที่คุ้มที่สุดคือ
   "output ขนาดเท่า input" (69.77% ของ pair, 67.50% ของ task) ส่วนที่เหลือต้องคำนวณขนาด
   จากโครงสร้างในภาพ การจำ "ขนาด output คงที่" ช่วยได้แค่ 1/120 task

4. **จำกัด palette ของคำตอบไว้ที่สีของ input เป็น prior ที่ดี แต่ไม่ใช่ constraint แข็ง**
   87.83% ของ pair ใน evaluation มี output palette ⊆ input palette ถ้าบังคับเป็นกฎตายตัว
   จะตัดคำตอบที่ถูกทิ้งไปไม่เกิน 12.17% ของ pair — คุ้มถ้าใช้เป็น bias ในการ search
   แต่ต้องเปิดช่องให้สร้างสีใหม่ได้ และต้องระวังว่าใน training อัตราการเติมสีใหม่สูงกว่า
   ถึง 30.18% วิธีที่จูนบน training จะมีแนวโน้ม "แต่งสี" เกินจริงเมื่อไปเจอ evaluation

5. **งบ compute ที่วัดบน training จะต่ำกว่าความจริงราวสองเท่า** — evaluation มี
   mean input cells 401.24 เทียบกับ 184.66 (2.17×) และ mean object ต่อ input grid 27.23
   เทียบกับ 14.70 (1.85×) วิธีที่ค้นหาแบบ combinatorial บน object จะโตเร็วกว่าเชิงเส้น
   ตามจำนวน object ฉะนั้นต้องตั้ง time budget และทดสอบ scaling บนงานขนาด evaluation
   ตั้งแต่แรก ไม่ใช่วัดบน training แล้วคูณสอง

6. **prior เรื่อง symmetry ครอบคลุม evaluation น้อยกว่าที่ training ทำให้รู้สึก** —
   input ที่สมมาตรอย่างน้อยหนึ่งแบบ: training 12.26% แต่ evaluation 4.56%
   (output 22.93% vs 13.50%) solver แนว symmetry-repair ยังมีที่ยืน แต่เป็นส่วนแบ่งเล็ก
   ของ evaluation ไม่ควรเป็นแกนหลักของวิธี

7. **การให้คะแนนแบบ all-or-nothing ทำร้าย evaluation มากกว่า** — 37.50% ของ task ใน
   evaluation มี test input มากกว่าหนึ่ง (เทียบกับ 6.90% ใน training) และ task จะนับว่า
   แก้ได้ก็ต่อเมื่อ **ทุก** test input ถูก ความสามารถต่อ output เท่ากันจึงให้คะแนนระดับ
   task ต่ำกว่าบน evaluation โดยอัตโนมัติ — เวลาเทียบตัวเลข training กับ evaluation
   ต้องรู้ว่าส่วนหนึ่งของช่องว่างมาจากโครงสร้างการให้คะแนน ไม่ใช่ความยากของ task ล้วน ๆ
   และควรรายงานทั้ง per-task และ per-test-input accuracy

8. **demonstration น้อย (median 3, min 2 ทั้งสอง split)** — mean ของ evaluation คือ
   2.992 ต่ำกว่า training 3.232 เล็กน้อย วิธีที่ต้องเรียนพารามิเตอร์จาก demonstration
   จำนวนมากใช้ไม่ได้ ตัวเลขนี้บังคับให้วิธีต้องเป็น few-shot induction ที่ prior แข็ง
   ไม่ใช่การ fit

9. **เรื่องระเบียบการทดลอง** — ความต่างที่วัดได้ในข้อ 2, 3, 5 แปลว่า hyperparameter หรือ
   threshold ใด ๆ ที่จูนบน training (โดยเฉพาะที่เกี่ยวกับ background, ขนาด grid, จำนวน
   object) จะ transfer ไม่ดี ควรกันชุด validation ที่แยกจาก evaluation ไว้ต่างหาก และ
   รายงานคะแนนทั้งสอง split เสมอ ตามกติกาเหล็กใน `docs/ROADMAP.md`

---

*ตัวเลขทั้งหมดข้างบนออกจาก `arc2/scripts/analyze_tasks.py` เมื่อ 2026-09-10 บน dataset
checkout `f3283f7` — รันใหม่ได้ด้วยคำสั่งในหัวข้อ Provenance และค่าที่ได้จะเท่าเดิม
ทุกครั้ง (deterministic)*
