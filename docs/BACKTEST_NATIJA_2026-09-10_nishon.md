# Nishon qoidasi o'lchovi — va undan chiqqan KATTAROQ savol

Sana: 2026-09-10
Actions: 93296009361 (birinchi), 93303020009 (A/B)
Coinlar: 12 ta, 730 kun, alternativ zanjir (jonli tizim yuritadigan)

---

## 1. Savol

2026-09-10 da loyiha egasi jonli signallar ro'yxatini ko'rsatdi:
~90 foizi "Bekor qilingan", bir xil coin bir xil foiz bilan
o'nlab marta takrorlangan.

Ikkita xato topildi va tuzatildi (`ARXITEKTURA.md` #99). Ulardan
biri — **"TP1 joriy narxdan yuqori bo'lsin"** qoidasi.

Savol: bu qoida natijaga qanday ta'sir qildi?

---

## 2. Javob — qoida deyarli TEGMAYDI

| konfiguratsiya | signal | foydali | PF | o'rt.% | jami% | pasayish |
|---|---|---|---|---|---|---|
| nishon qoidasi YO'Q | 66 | 34.8% | 1.03 | +0.05 | +3.2% | 37.8% |
| nishon qoidasi BILAN | 64 | 29.7% | 0.90 | −0.21 | −13.4% | 52.8% |

**Savdo soni farqi — 2 ta.**

Qoida 779 nomzodni rad etdi, lekin ularning deyarli hammasi
baribir savdoga aylanmasdi:

* 496 tasini "TP1/Stop nisbati past" qoidasi baribir rad etardi
  (qoidasiz variantda o'sha sanoq 104 → 600 ga ko'tarildi);
* qolgan ~281 tasi "bekor" bo'lardi — ya'ni limit bajarilmay,
  savdo umuman ochilmasdi. **Aynan shu — loyiha egasi ekranda
  ko'rgan 90 foiz.**

### Xulosa

Qoida o'z ishini qildi: u **bekor qilinadigan signallar oqimini**
kesdi va boshqa deyarli hech narsaga tegmadi. Muammoning sababi
emas edi.

---

## 3. LEKIN — kattaroq muammo ochildi

Ikkala variant ham PF ≈ 1.0. Ya'ni **ustunlik (edge) YO'Q**.

66 savdoda ikkita savdo natijani +3.2% dan −13.4% ga o'zgartiradi.
Bu — shovqin, natija emas. Bunday namunada "PF 1.03" ham,
"PF 0.90" ham bir xil narsani aytadi: **o'lchanmadi**.

### Eski raqam bilan solishtirish

| | Savdo | Foydali | PF | Jami |
|---|---|---|---|---|
| 2026-09-04, to'liq zanjir | 277 | 68.2% | **3.50** | +770% |
| 2026-09-10, alternativ zanjir | 66 | 34.8% | **1.03** | +3.2% |

277 → 66. Bu farqning katta qismi **mening tuzatishimdan EMAS**
(u atigi 2 ta savdoga tegdi).

Oradagi asosiy o'zgarish — **2026-09-09** da qo'shilgan qoida.
Kodning o'zi buni yozib qo'ygan (`zanjir_engine.py`):

> "2026-09-09 gacha bu bosqich YO'Q edi: backtest savdoni darrov
> `entry` narxida ochardi, narx o'sha paytda entry'dan yuqorida
> bo'lsa ham. Ya'ni o'lchov bozor bermagan narxda sotib olgandek
> hisoblardi."

Ya'ni **PF 3.50 — bozorda mavjud bo'lmagan narxlarda sotib olish
hisobiga chiqqan raqam.** 277 "savdo"ning ~211 tasi hech qachon
ochilmasdi.

🔴 **PF 3.49 / 3.50 raqamlari endi ishlatilmaydi.**

---

## 4. Keyingi o'lchov

Bu yugurish ALTERNATIV zanjirni o'lchadi — jonli tizim aynan shuni
yuritadi. Eski 3.50 esa ASOSIY zanjirniki edi (`zanjir_backtest`).
Ikkalasi boshqa zanjir.

Shuning uchun keyingi savol: **asosiy zanjir bugungi halol kodda
qanday chiqadi?** Agar u sezilarli yaxshi bo'lsa, alternativ
yo'llar (zaif blokni "qutqarish") signal sifatini pasaytiryapti
degani bo'ladi — va jonli tizim aynan o'shani ishlatyapti.

    Actions -> Zanjir o'lchovi -> olchov: backtest

O'lchanmaguncha alternativ yo'llar haqida xulosa chiqarilmaydi.
