# Tahlil moduli: mexanizm tahlili

**Sana:** 2026-09-02 · **Manba:** `core/analysis/` kodining o'zi, taxmin emas
**Vizual xarita:** artifact — "Hom ashyodan mahsulotgacha"

Bu hujjat KOD O'ZGARTIRMAYDI. U mavjud mexanizmni yozib qo'yadi, chunki
uchta backtest natijasini (`BACKTEST_NATIJA_*.md`) faqat shu tushuntiradi.

---

## 1. Kim "yo'q" deya oladi

`classic_ta.analyze()` dan o'qildi. Uchta darvoza bor:

| Manba | Nima aytadi | Qaror |
|---|---|---|
| `halal_screening` | Coin halolmi | **DARVOZA** |
| S/R zonasi | Narx support zonasida va arzon yarmidami | **DARVOZA** |
| `build_levels` | Stop va TP arifmetikaga sig'dimi | **DARVOZA** |
| SMC struktura | Bozor ko'tarilishdami | faqat ball |
| Kunlik trend | Katta rasm mosmi | faqat ball |
| Indikatorlar | RSI · MACD · hajm tasdiqlaydimi | faqat ball |
| Daraja turi | Bu qanday support — kuchlimi | faqat ball |
| Likvidlik yalash | Yolg'on harakat bo'ldimi | faqat ball |
| Kill Zone · QT | Vaqt qulaymi | faqat ball |

Sozlamada uchta `require_*` bayrog'i bor va **uchalasi ham `false`**:
`require_htf_alignment`, `require_confirmation`,
`require_structure_alignment`.

Uchta darvozaning uchalasi ham geometriya va arifmetika. **Hech biri
sifat haqida emas.**

## 2. O'lik tarmoq

`setup_qualified` — metodikaning to'liq shartnomasi (SMC + daraja turi
+ yalash birgalikda) — kodda BITTA joyda ishlatiladi:

    core/analysis/scoring/scorer.py:173
        setup_complete=nomzod.setup_qualified,

Ekranga yozish uchun. Qarorga ta'siri yo'q.

## 3. Nima uchun filtrlar ishlamadi

Ikki vazifa o'rin almashgan:

- SIFAT dalillari (struktura, confluence, yalash) — tartiblaydi
- PORTFEL holati (ochiq signal, korrelyatsiya, ketma-ket zarar) — qaror qiladi

Natija: tizim nomzodlarni tartiblab eng yuqorisini oladi — uyumning
o'zi yomon bo'lsa ham. Sifat darvozasi yo'q.

Bu 3-backtest natijasini to'liq tushuntiradi: to'rtta filtr, signal
soni 454 dan 667 gacha, **win-rate 37.3–38.0% da qotib qoldi**.
Filtrlar uyumga kim kirishini o'zgartirdi, uyum baribir tartiblanib
eng yuqorisi olinaverdi.

## 4. Sanoat naqshlari bilan solishtirish

### Alpha → Portfolio → Risk → Execution

| Naqshda | Sizda | Holat |
|---|---|---|
| Universe | `halal_screening` | bor — kuchli tomon |
| Alpha | `strategiyalar` | bor, lekin **muddat va ishonch chiqarmaydi** |
| Portfolio | `position_sizing` | bor |
| Risk | `risk_engine` | bor (13 qoida) |
| Execution | bot va sayt | bor |

Naqshda Alpha `Insight` chiqaradi: yo'nalish, ishonch, **muddat**.
Sizda muddat umuman yo'q — shuning uchun o'rtacha ushlash 42.9 soat,
bozor esa ikki yilda +33% o'sgan.

### Fakt bir marta hisoblanadi

`analyze_structure()` YETTITA joyda chaqiriladi: `runner`, `backtest`,
ikkala strategiya, `market_health/inputs`, `quarterly`,
`market_structure`. Bitta fakt haqida yettita javob bo'lishi mumkin —
bugun topilgan uchta backtest/jonli farqi aynan shundan.

### Voronka va sabab

Bu sizda naqshdan YAXSHIROQ. Har bir rad etishning nomi va sababi bor.
Saqlanadi va yangi qatlamlarga ham qo'llanadi.

## 5. Retsept

Bitta jumlada: **struktura va kunlik trend balldan darvozaga ko'chadi.**
Ular allaqachon hisoblangan — faqat ovozi yo'q edi.

Tartib:

1. **Fakt qatlami ajratiladi** — bir marta hisoblanadi, hamma o'qiydi
2. **Sifat darvozalari yoqiladi** — bayroqlar bor, kod yozilmaydi
3. **Ball faqat tartiblaydi** — omon qolganlar orasida
4. **Nomzodga MUDDAT qo'shiladi** — hozir bu savol berilmaydi
5. **Har qadam ALOHIDA o'lchanadi** — birga yoqilsa qaysi biri
   ishlaganini bilib bo'lmaydi

Yangi indikator qo'shilmaydi. Yangi strategiya yozilmaydi.

## 6. Muhim ogohlantirish

2-qadam bugun RAD ETILGAN gipoteza bilan bir xil emas.

"Kunlik trend majburiy" varianti alohida sinaldi va win-rate'ni
ko'tarmadi (37.8% — deyarli o'zgarishsiz). Retseptda u fakt qatlami va
boshqa darvozalar BILAN BIRGA ishlaydi.

Bu ham gipoteza. O'lchanmaguncha shunday qoladi.
