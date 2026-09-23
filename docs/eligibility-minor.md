# สิทธิ์เข้าแข่งเมื่อผู้เข้าแข่งยังไม่บรรลุนิติภาวะ — เอกสารลงมือทำ

> **ตัวบทกติกาและแหล่งอ้างอิงอยู่ที่ [`competition-brief.md`](competition-brief.md) §7**
> ไฟล์นี้ไม่ทวนซ้ำ — มีไว้เพื่อ**ลงมือทำ** เพราะเป็นงานที่ต้องรอคำตอบจากคนอื่น
>
> ค้นเพิ่มเมื่อ **23 ก.ย. 2026** · ยังเปิด `kaggle.com` จาก container ไม่ได้
> ⚠️ **ผมไม่ใช่ทนาย นี่ไม่ใช่คำแนะนำทางกฎหมาย** ต้องยืนยันกับหน้าจริงก่อนใช้

## 1. สิ่งที่เราเคยเข้าใจผิด

`README.md` เคยเขียนว่า *"ถ้าชนะ ผู้ปกครองต้องลงนามภายใน 7 วัน"*
ประโยคนี้จริง แต่**ทำให้เข้าใจว่าเป็นงานหลังประกาศผล** ซึ่งไม่ใช่ มีสองชั้น:

| ชั้น | เรื่อง | ต้องเสร็จเมื่อไหร่ | เคยรู้ไหม |
|---|---|---|---|
| **1. สิทธิ์เข้าแข่ง** | ต้องได้ทั้ง Sponsor agreement **และ** guardian consent | **ก่อน entry deadline** | ❌ ไม่ชัด |
| 2. เอกสารตอนชนะ | ผู้ปกครองลงนามใน 7 วัน ไม่งั้นสละสิทธิ์ | หลังประกาศผล | ✅ |

**ชั้น 1 ต่างหากที่เป็นตัวตัดสิน** และเป็นชั้นที่เรายังไม่ได้เริ่มเลย

## 2. ทำไมต้องเริ่มวันนี้ ไม่ใช่ตอนงานเสร็จ

- เกณฑ์อายุที่ใช้กับไทยคือ **20 ปี** (ไม่ใช่ 18) — ดู brief §7
- ทางออกในกติกาคือ exception clause ซึ่ง **ต้องให้ Sponsor ตกลง**
- brief §11 บันทึกไว้ว่า **ไม่พบกรณีตัวอย่างจริงที่ ARC Prize เคยอนุมัติให้ผู้เยาว์**
  → ไม่รู้ว่าเขาจะตอบว่าอย่างไร และไม่รู้ว่าใช้เวลานานแค่ไหน
- เรื่องนี้ **ไม่ขึ้นกับคุณภาพงานเลย** งานดีที่สุดในรายการก็ยังเสียสิทธิ์ได้

> **ความเสี่ยงที่แท้จริงไม่ใช่ "ถูกปฏิเสธ" แต่คือ "ตอบช้าจนเลย deadline"**

## 3. Checklist

- [ ] **1. ส่งอีเมลหา `team@arcprize.org`** (ร่างอยู่ข้อ 4 — ส่งได้เลย)
- [ ] **2. เปิด `kaggle.com/consent-minors-process` อ่านเอง** แล้วจดว่าต้องใช้เอกสารอะไร
      ใครเซ็น ส่งไปที่ไหน มีกำหนดเวลาไหม
      (⚠️ **คนละฉบับกับ** `kaggle.com/guardian-consent-minor-use` ซึ่งเป็นแค่สิทธิ์ใช้เว็บ
      ถ้าเคยเซ็นตอนสมัครบัญชี ฉบับนั้น**ไม่ครอบคลุม**การเข้าแข่ง)
- [ ] **3. เปิดหน้า Rules อ่านหัวข้อ eligibility ด้วยตาตัวเอง** — ผมยืนยันแทนไม่ได้
      `kaggle.com/competitions/arc-prize-2026-paper-track/rules`
      `kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules`
- [ ] **4. คุยกับผู้ปกครองตั้งแต่ตอนนี้** ว่าจะต้องมีการลงนาม และอาจต้องใช้เอกสารแสดงตน
- [ ] **5. เก็บสำเนาทุกฉบับ + วันที่ส่ง + อีเมลตอบกลับ** ไว้ในที่เดียว

## 4. ร่างอีเมล (แก้ชื่อแล้วส่งได้)

```
To: team@arcprize.org
Subject: Eligibility question — entrant under the age of majority (Thailand)

Hello,

I am preparing a submission for ARC Prize 2026 (ARC-AGI-3 track, with a
corresponding Paper Track writeup). Before I go further I would like to
confirm my eligibility.

I am a resident of Thailand and I am under 20, which is the age of majority
here. As I read the competition rules, the age requirement is the older of 18
or the age of majority in my jurisdiction, unless the Sponsor agrees otherwise
and appropriate parental/guardian consent is obtained.

Could you tell me:

1. Whether an entrant in my situation may enter this competition at all.
2. If so, what consent documentation you need, who must sign it, and where to
   send it.
3. By when it must be received — in particular whether it must be on file
   before the entry deadline rather than after results are announced.
4. Whether entering as part of a team whose registered entrant is an adult
   would be acceptable, or whether that would itself breach the rules.

My work is open source under MIT-0 at github.com/Panus15/arc-prize-2026.

Thank you for your time.

<ชื่อจริง>
<อีเมล> · <ประเทศ: Thailand>
```

**ทำไมถามข้อ 4 ด้วย:** Paper Track รับทีม 1–8 คน (brief §2.5) การลงเป็นทีมโดยมี
ผู้ใหญ่เป็นผู้สมัครเป็นทางออกที่ดูเข้าท่า **แต่ห้ามทำเองโดยไม่ถาม** เพราะการตั้งทีม
เพื่อเลี่ยงเกณฑ์อายุอาจผิดกติกาในตัวมันเอง ให้เขาตอบเป็นลายลักษณ์อักษรก่อน

## 5. บันทึกความคืบหน้า

| วันที่ | ทำอะไร | ผล |
|---|---|---|
| 23 ก.ย. 2026 | เขียนเอกสารนี้ · ยังไม่ได้ส่งอีเมล | — |
