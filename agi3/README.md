# agi3 — ARC-AGI-3

สนามหลักของการเข้าแข่ง ARC Prize 2026

## ทำไมมี environment ของตัวเอง

SDK จริงคุยกับ server ระยะไกลและกินโควตา scorecard ทุกครั้งที่ยิง action
ซึ่งไม่เหมาะกับการวน develop policy `arcagi3/mock.py` จึงจำลอง environment
ที่ **ใช้ type จริงจาก `arcengine`** (`FrameData`, `GameAction`, `GameState`)
แต่รันในเครื่อง ไม่ต้องมี API key และ**รู้จำนวน action ที่น้อยที่สุดของแต่ละด่าน**
ทำให้วัดประสิทธิภาพได้จริงแทนที่จะเดา

policy ที่เขียนที่นี่ย้ายไปรันกับของจริงได้โดยไม่ต้องแก้

## ใช้งาน

```bash
./setup.sh                 # ต้องมี Python 3.12 (SDK บังคับ)
.venv/bin/pytest
.venv/bin/python -m arcagi3 play              # รันทุก agent
.venv/bin/python -m arcagi3 play --agent greedy
```

## ผลปัจจุบัน

```
random     truncated  levels 2/3  actions 500 (baseline 30, efficiency 6.00%)
greedy     WIN        levels 3/3  actions 30  (baseline 30, efficiency 100.00%)
```

`greedy` จบที่ **30 action เท่ากับ baseline พอดี** — ยืนยันว่า environment แก้ได้จริง
และ baseline คำนวณถูก ส่วน `random` คือพื้นที่ต้องเอาชนะ

## โครงสร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `arcagi3/actions.py` | คำศัพท์ action + ทางแก้กับดัก `GameAction(int)` |
| `arcagi3/mock.py` | environment จำลองที่พูดภาษาเดียวกับของจริง |
| `arcagi3/agent.py` | base agent (บังคับเลือกเฉพาะ action ที่ legal) + random/greedy |
| `arcagi3/budget.py` | รันเกม + นับ action เทียบ baseline |
| `API-NOTES.md` | บันทึก API จริงจากการ introspect package |

## หลักการออกแบบ

**เลือกได้เฉพาะ action ที่ frame บอกว่าใช้ได้** — `BaseAgent.act()` ตรวจให้ ถ้า policy
เลือกผิดจะ raise ทันทีตอนพัฒนา แทนที่จะเงียบ ๆ เสีย action ไปในรอบที่คิดคะแนนจริง

**action ที่ผิดกฎก็ยังเสียเทิร์น** — เพราะ scorecard จริงนับทุก action
policy ที่ไม่อ่าน `available_actions` จึงต้องโดนลงโทษที่นี่ด้วย ไม่ใช่ได้ลองใหม่ฟรี
