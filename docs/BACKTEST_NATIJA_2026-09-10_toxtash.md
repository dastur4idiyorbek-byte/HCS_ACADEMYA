# TO'XTASH QOIDASI ISHGA TUSHDI — hech bir variant PF 1.0 dan yuqori emas

Sana: 2026-09-10
Actions: 93309823468 (`olchov: backtest`), 93303020009 (`alternativ`)
Coinlar: 12 ta, 730 kun, xarajat 0.3%/savdo

---

## 1. Barcha o'lchangan variantlar

| Variant | Savdo | Foydali | PF | Jami | Pasayish |
|---|---|---|---|---|---|
| alternativ zanjir (JONLI TIZIM) | 66 | 34.8% | **1.03** | +3.2% | 37.8% |
| alternativ + nishon qoidasi | 64 | 29.7% | **0.90** | −13.4% | 52.8% |
| to'liq zanjir (4 blok) | 153 | 35.3% | **0.83** | −65.3% | 82.2% |
| 11 bo'sh tekshiruvsiz | 125 | 34.4% | **0.74** | −87.6% | 100.8% |
| tasdiqlashsiz (3 blok) | 194 | 33.5% | **0.71** | −148.0% | 169.9% |
| faqat fundamental+struktura | 194 | 33.5% | **0.71** | −148.0% | 169.9% |
| zanjirsiz — faqat darajalar | 310 | 37.7% | **0.84** | −123.0% | 147.2% |

Skriptning o'z xulosasi:

> ⚫ Eng yaxshi PF 0.84 — 1.0 dan past. TO'XTASH QOIDASI: natija
> admin bilan muhokama qilinadi, keyingi qadam BIRGA hal qilinadi
> (2-prompt, 8-qism, 5-band).

---

## 2. ENG MUHIM FAKT — zanjir hech narsa qo'shmayapti

    zanjirsiz — faqat darajalar     310 savdo   PF 0.84
    to'liq zanjir (4 blok)          153 savdo   PF 0.83

Zanjir 8000 dan ortiq nomzodni 153 taga qisqartiradi. Natija esa
**zanjirsiz bilan bir xil** (0.83 va 0.84 — farq shovqin ichida).

Ya'ni: Struktura, Tasdiqlash, Zona Sifati va Fundamental bloklari
signalni **saralamayapti**. Ular signal SONINI kamaytiradi, lekin
qolganlarning SIFATINI oshirmaydi.

Bu — modulning butun mantiqiga tegadigan xulosa.

---

## 3. G'alaba foizi va nisbat bir-biriga mos emas

Hamma variantda foydali savdo **33–38%**.

TP1/Stop nisbatining minimal poli — **1.2**. 1.2 nisbatda nolga
chiqish uchun g'alaba foizi ~45% bo'lishi kerak (xarajatsiz ham).
35% bilan tizim matematik ravishda yutqazadi.

Ikki yo'ldan biri kerak:

* g'alaba foizini oshirish (kirish sifati), yoki
* nisbatni ko'tarish (masalan 1.2 → 2.0+), ya'ni kamroq lekin
  kattaroq nishon.

Ikkalasi ham O'LCHANMAGAN. Qaysi biri to'g'ri ekani taxmin
qilinmaydi — `--tp1-nisbat` bayrog'i bilan o'lchanadi.

---

## 4. Nima aniq BO'LMADI

* **730 kun — yagona davr.** Bu 2024–2026 oynasi. Boshqa davrda
  natija boshqacha bo'lishi mumkin (`--end-date` bilan sinaladi).
* **12 coin — kichik to'plam.** Jonli tizim 80 coinda ishlaydi.
* **66–310 savdo — kam namuna.** Alternativ zanjirda ikkita savdo
  natijani +3.2% dan −13.4% ga o'zgartirdi.

Shuning uchun "tizim yutqazadi" ham qat'iy xulosa emas. Qat'iy
bo'lgani: **ustunlik hech bir variantda ko'rinmadi.**

---

## 5. Tavsiya

Jonli tizim hozir obunachilarga signal yuboryapti. O'lchov esa
ustunlik yo'qligini ko'rsatdi.

**Tavsiya: avtomatik signal tarqatish TO'XTATILSIN** — ustunlik
o'lchanmaguncha. Sayt, akademiya, bozor holati va qo'lda signal
ishlayveradi.

Qaror loyiha egasiniki. Bu hujjat faqat raqamlarni beradi.
