# สิ่งที่คุณต้องทำ — และสิ่งที่ผมทำต่อเองได้หลังจากนั้น

> เขียน **25 ก.ย. 2026** · milestone #2 เหลือ **5 วัน** (30 ก.ย.) · ปิดรับ **เหลือ 45 วัน** (9 พ.ย. 23:59 UTC)
>
> **หลักการ:** คุณทำเฉพาะสิ่งที่ต้องใช้ตัวตน บัญชี หรืออินเทอร์เน็ตของคุณ
> ส่วนที่เหลือผมทำเองทั้งหมด ทุกขั้นด้านล่างบอกไว้ว่า **ทำเสร็จแล้วส่งอะไรกลับมาให้ผม**

## สรุปหน้าเดียว

| ขั้น | ทำอะไร | เวลา | ส่งอะไรกลับมา | ปลดล็อกอะไร |
|---|---|---|---|---|
| **1** | ส่งอีเมลถาม ARC Prize เรื่องอายุ | 5 นาที | "ส่งแล้ว" + คำตอบเมื่อได้ | สิทธิ์เข้าแข่ง |
| **2** | ดาวน์โหลดเกมจริง → ใส่ private repo | 20 นาที | ชื่อ repo | **ผมรันเกมจริงเองได้ทั้งหมด** |
| **3** | อัปโหลด notebook เข้า Kaggle แล้วกด Submit | 15 นาที + รอ | คะแนนที่ได้ | เกณฑ์ Accuracy |
| **4** | อ่านหน้า consent ของ Kaggle + คุยกับผู้ปกครอง | 15 นาที | สิ่งที่หน้านั้นขอ | เอกสารยินยอม |

**ขั้น 1 กับ 2 สำคัญที่สุด ทำวันนี้ได้เลย** ขั้น 2 คือขั้นที่เปลี่ยนเกมที่สุด —
หลังจากนั้นผมรันเกมจริง วัดผล แก้ agent และเติมเปเปอร์เองได้โดยไม่ต้องรอคุณอีก

---

## ขั้น 1 — ส่งอีเมลเรื่องสิทธิ์เข้าแข่ง (5 นาที)

ร่างอีเมลอยู่ใน [`eligibility-minor.md`](eligibility-minor.md) ข้อ 4 — แก้ชื่อแล้วส่งถึง
**`team@arcprize.org`** ได้เลย

**ทำไมต้องวันนี้:** เกณฑ์อายุของไทยคือ 20 ปี และทางออกต้องให้ **ผู้จัดตกลง + ผู้ปกครองยินยอม
ก่อนสมัคร** เรารอคำตอบเขาอยู่ ยิ่งส่งช้ายิ่งเสี่ยงเลยกำหนด และเรื่องนี้ไม่เกี่ยวกับคุณภาพงานเลย

**ส่งกลับมา:** บอกผมว่า "ส่งแล้ว" และเมื่อเขาตอบ ให้คัดลอกคำตอบมาให้ผม

---

## ขั้น 2 — ดาวน์โหลดเกมจริง แล้วส่งให้ผมผ่าน private repo (20 นาที)

**ทำไม:** เกมของ ARC-AGI-3 เป็นไฟล์ source ที่รันในเครื่องได้โดยไม่ต้องต่อเน็ต
(Kaggle ก็ให้คะแนนแบบนั้น) แต่การ **ดาวน์โหลดครั้งแรก** ต้องต่อ `arcprize.org`
ซึ่ง container ของผมถูกบล็อก พอไฟล์มาถึงผม ผมทำทุกอย่างที่เหลือได้เอง
ผมทดสอบเส้นทางนี้ครบแล้วด้วยเกมจำลอง (ดูท้ายไฟล์)

### 2.1 เตรียมเครื่อง (ครั้งเดียว)

ต้องมี **Python 3.12** และ **git**

- Windows: ติดตั้ง Python 3.12 จาก python.org (ติ๊ก *Add python.exe to PATH*) และ Git จาก git-scm.com
- ตรวจ: เปิด PowerShell แล้วพิมพ์ `py -3.12 --version` ต้องขึ้น `Python 3.12.x`

### 2.2 โหลดโปรเจกต์และติดตั้ง

**Windows (PowerShell):**
```powershell
git clone https://github.com/Panus15/arc-prize-2026.git
cd arc-prize-2026\agi3
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

**macOS / Linux:**
```bash
git clone https://github.com/Panus15/arc-prize-2026.git
cd arc-prize-2026/agi3
./setup.sh
```

### 2.3 ใส่ API key — ในไฟล์ ไม่ใช่ในแชต

> key ที่คุณเคยวางในแชตไว้ **ควรออกใหม่** ที่หน้า API key ของ arcprize.org แล้วใช้ตัวใหม่
> ไฟล์ `.env` ถูก gitignore ไว้แล้ว จะไม่หลุดขึ้น GitHub

**Windows (PowerShell)** — ต้องมี `-Encoding ascii` ไม่งั้น PowerShell อาจเขียนไฟล์เป็น UTF-16 ซึ่งอ่านไม่ออก:
```powershell
Set-Content -Path .env -Value "ARC_API_KEY=ใส่คีย์ตรงนี้" -Encoding ascii
```

**macOS / Linux:**
```bash
printf 'ARC_API_KEY=%s\n' 'ใส่คีย์ตรงนี้' > .env && chmod 600 .env
```

### 2.4 เช็คการเชื่อมต่อ (ไม่กินโควตาอะไร)

```powershell
.venv\Scripts\python scripts\check_live.py        # Windows
.venv/bin/python scripts/check_live.py            # macOS / Linux
```

ต้องเห็น `connection OK — N games reachable` — สคริปต์พิมพ์แค่ **ความยาว** ของ key ไม่พิมพ์ตัว key

| ถ้าเจอ | แปลว่า | ทำอะไร |
|---|---|---|
| `connection OK` | ใช้ได้ | ไป 2.5 |
| `the server rejected the key (401)` | key ผิด/หมดอายุ | ออก key ใหม่ แล้วทำ 2.3 ซ้ำ |
| `could not reach ...` | เน็ต/firewall | ลองเน็ตอื่น |

### 2.5 ดาวน์โหลดเกมทั้งหมด

```powershell
.venv\Scripts\python scripts\fetch_games.py       # Windows
.venv/bin/python scripts/fetch_games.py           # macOS / Linux
```

ไฟล์จะอยู่ในโฟลเดอร์ `agi3\environment_files\` พร้อม `MANIFEST.json`
ท้ายสุดต้องขึ้น `N downloaded, 0 failed`

### 2.6 สร้าง private repo บน GitHub

1. เปิด **https://github.com/new**
2. Repository name: **`arc-games-private`**
3. เลือก **Private** ← สำคัญ
4. **ไม่ต้อง**ติ๊ก README / .gitignore / license
5. กด **Create repository**

> ⚠️ **ห้ามใส่ไฟล์เกมใน `arc-prize-2026`** — repo นั้นเป็น public และ MIT-0
> ไฟล์เกมเป็นของ ARC Prize ไม่ใช่ของเรา `.gitignore` กันไว้แล้ว แต่อย่าฝืน

### 2.7 push ไฟล์เกมขึ้น repo นั้น

**Windows (PowerShell):**
```powershell
cd environment_files
git init -b main
git add .
git commit -m "ARC-AGI-3 public games"
git remote add origin https://github.com/Panus15/arc-games-private.git
git push -u origin main
```
(macOS / Linux ใช้คำสั่งเดียวกัน)

ถ้า git ถามชื่อ/อีเมลก่อน commit ให้ตั้งครั้งเดียว:
`git config --global user.name "Panus15"` และ `git config --global user.email "อีเมลคุณ"`

### 2.8 ให้ Claude เข้าถึง repo นั้น

เปิด **https://claude.ai/connect-github** แล้วดูว่า Claude GitHub App เข้าถึง
`arc-games-private` ได้ — ถ้าตอนติดตั้งเลือกแบบ *Only select repositories* ต้องเพิ่ม repo นี้เข้าไป

### 2.9 ส่งกลับมา

พิมพ์บอกผมว่า **"push แล้ว: Panus15/arc-games-private"** — แค่นั้น

---

## ขั้น 3 — ส่ง notebook เข้า Kaggle (15 นาที + รอรัน)

notebook สร้างไว้ให้แล้ว ไม่ต้องแก้อะไร: `agi3/submission/kaggle/submission.ipynb`

> **หมายเหตุเรื่องอายุ:** การกด *accept rules* และ submit คือการ "เข้าแข่ง"
> ถ้าผู้จัดตอบว่าผู้เยาว์ต้องมีเอกสารก่อน entry นั้นอาจต้องถอน — **ผมแนะนำให้ส่งอีเมลขั้น 1 ก่อน**
> แล้วค่อยทำขั้นนี้ ทางที่ดีที่สุดคือทำตอนผู้ปกครองรับรู้ด้วย
> อีกด้าน: กติกาบอกว่า **คะแนนเท่ากัน คนเข้าก่อนชนะ** การรอนานก็มีราคา — การตัดสินใจนี้เป็นของคุณ

### 3.1 ยอมรับกติกาการแข่ง
เปิด https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules แล้วกดยอมรับ

### 3.2 ดาวน์โหลด notebook
เปิดลิงก์นี้แล้วบันทึกไฟล์:
https://github.com/Panus15/arc-prize-2026/raw/main/agi3/submission/kaggle/submission.ipynb

### 3.3 นำเข้า Kaggle
kaggle.com → **Code** → **New Notebook** → เมนู **File** → **Import Notebook** → เลือกไฟล์ที่เพิ่งโหลด

### 3.4 ผูกข้อมูลของการแข่ง
แผงขวา → **Add Input** → ค้น `ARC Prize 2026 - ARC-AGI-3` → กด **+** ให้เป็น Input

(notebook อ่านไฟล์ runner และ wheel จาก `/kaggle/input/competitions/arc-prize-2026-arc-agi-3/`
ถ้าไม่ผูก ขั้น 3.6 จะหยุดพร้อมข้อความ `runner not found`)

### 3.5 ตั้งค่า session
แผงขวา → **Settings / Session options**: **Accelerator = None**, **Internet = Off**
(agent ของเราไม่ใช้ GPU ไม่ต้องเผาโควตา)

### 3.6 Save & Run All
มุมขวาบน **Save Version** → **Save & Run All (Commit)** → รอจนสถานะเป็น complete

**เปิด log ดู ต้องมีสองบรรทัดนี้:**
```
self-check: WIN 2 / 2 in 42 actions
SELF-CHECK PASSED
```
> ⛔ **ถ้าไม่มี `SELF-CHECK PASSED` — อย่ากด Submit** คัดลอก error ส่งมาให้ผม
> self-check นี้มีไว้เพื่อให้เจอปัญหาตรงนี้ ก่อนเสียโควตา submit (วันละ 5 ครั้ง)

### 3.7 Submit
หน้า notebook ที่ save แล้ว → **Submit to Competition** → Output file เลือก **`submission.parquet`** → Submit

### 3.8 ส่งกลับมา
รอ Kaggle รันเสร็จ (อาจนานเป็นชั่วโมง) แล้วดูคะแนนที่ **My Submissions** — ส่งตัวเลขมาให้ผม
ถ้ามี error ให้คัดลอกข้อความมาทั้งหมด

> ชื่อปุ่มในหน้า Kaggle อาจต่างจากที่เขียนเล็กน้อย — ผมเปิด kaggle.com จาก container ไม่ได้
> ขั้นตอนนี้อิงจาก ARC-AGI-3-Kaggle-Starter ของผู้จัดเอง ถ้าหาปุ่มไม่เจอ ถ่ายหน้าจอมาได้เลย

---

## ขั้น 4 — หน้า consent ของ Kaggle + ผู้ปกครอง (15 นาที)

1. เปิด **https://www.kaggle.com/consent-minors-process** (ฉบับ *เข้าแข่ง* — คนละฉบับกับ *ใช้เว็บ*)
2. จดว่าต้องใช้เอกสารอะไร ใครเซ็น ส่งที่ไหน มีกำหนดเวลาไหม → ส่งมาให้ผม
3. คุยกับผู้ปกครองว่าอาจต้องลงนาม และถ้าได้รางวัล ต้องเซ็นภายใน 7 วัน

รายละเอียดเต็ม: [`eligibility-minor.md`](eligibility-minor.md)

---

## สิ่งที่ผมจะทำเองทันทีที่ได้ของ

### เมื่อได้ขั้น 2 (ไฟล์เกม)

| ลำดับ | ผมทำอะไร | ทำไมลำดับนี้ |
|---|---|---|
| 1 | **รัน agent ตัวที่ล็อกไว้แล้ว** (tag `prereg-real-games`) บนเกมจริงทุกเกม เทียบกับ random | **ต้องทำก่อนแก้อะไรทั้งนั้น** — นี่คือการทดสอบคำทำนายในเปเปอร์ §6 ถ้าแก้ agent ก่อนแล้วค่อยวัด ผลจะไม่ใช่การทดสอบอีกต่อไป |
| 2 | บันทึกผลลง `paper/data/real-games-measured.json` พร้อม commit และคำสั่งทำซ้ำ | ตัวเลขทุกตัวต้องย้อนกลับไปหาที่มาได้ |
| 3 | เติมเปเปอร์ §1 ปิดท้าย และ §8 — ภายในเพดาน 1,500 คำ | ส่วนที่รอผลจริงอยู่ |
| 4 | **ปรับ agent กับเกมจริง** — เป็นครั้งแรกที่มีของจริงให้ปรับ แยก commit ชัดเจนว่าก่อน/หลัง | ผลก่อนปรับคือหลักฐานของเปเปอร์ ผลหลังปรับคือคะแนน |
| 5 | rebuild notebook + ทดสอบในสภาพจำลอง Kaggle ทั้งสองรอบ แล้วบอกคุณให้ submit ใหม่ถ้าดีขึ้นจริง | ไม่ให้คุณเสียโควตากับเวอร์ชันที่ไม่ดีกว่า |

### เมื่อได้ขั้น 3 (คะแนน Kaggle)
ใส่คะแนนจริงในเปเปอร์ และปรับตารางคำนวณเกณฑ์ Accuracy ใน ROADMAP ด้วยตัวเลขจริงแทนสมมติฐาน

### เมื่อได้ขั้น 1/4 (คำตอบเรื่องอายุ)
อัปเดต `eligibility-minor.md` และปรับแผนตามคำตอบ

---

## สิ่งที่ผมทดสอบไว้แล้ว — ทำไมมั่นใจว่าขั้น 2–3 จะใช้ได้

ผมเขียนเกมจำลอง 2 เกมในรูปแบบไฟล์เดียวกับที่ SDK ดาวน์โหลด (เดิน 1 เกม คลิก 1 เกม) แล้ว:

| ทดสอบอะไร | ผล |
|---|---|
| โหมด OFFLINE ของ SDK โหลดเกมจากไฟล์ | ✅ |
| agent ของเราผ่าน loop ของ runner ทางการ | ✅ ชนะทั้งสองเกม · scorecard 86.78 |
| **จำลอง Kaggle "Save & Run All"** (runner ทางการ + wheel จริงจาก PyPI) | ✅ `SELF-CHECK PASSED` · ออก `submission.parquet` ไฟล์เดียว |
| **จำลอง Kaggle รอบให้คะแนน** (game server โหมด competition ของ SDK เอง) | ✅ ทั้งสองเกมชนะ · scorecard **86.78 ตรงกับรันแบบ offline** |

การจำลองจับบั๊กได้ 2 ตัวก่อนถึงมือคุณ (`%%writefile` ไม่รับเซลล์ว่าง และไม่สร้างโฟลเดอร์ให้)
และระหว่างทางเจอบั๊กจริงอีกตัว: runner เล่นทุกเกมพร้อมกันคนละ thread แต่พิกัดคลิกถูกเก็บไว้ใน
object เดียวที่ทุก thread ใช้ร่วมกัน — คลิกของเกมหนึ่งอาจถูกส่งด้วยพิกัดของอีกเกม
ผมทำให้เกิดซ้ำได้แน่นอนแล้วแก้ พร้อมเทสกันกลับ

**สิ่งที่ยังไม่ได้ทดสอบ:** เกมจริง และหน้าเว็บ Kaggle จริง — สองอย่างนี้คือสิ่งที่ขั้น 2 กับ 3 ให้มา
