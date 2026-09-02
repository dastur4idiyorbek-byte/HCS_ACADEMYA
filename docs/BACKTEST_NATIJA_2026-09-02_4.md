# Backtest natijasi #4 — TAYANCH

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun | 4 380 qadam
**Kod:** `8c31a76` | GitHub Actions run #7

---

## Bitta raqam

```
Tayanch — olib ushlab turish: +33.0% (coinlar bo'yicha o'rtacha)
⚠️ Strategiya HECH NARSA QILMASLIKDAN yomon ishlagan.
```

Ogohlantirish **beshta variantning hammasida** chiqdi.

| | natija |
|---|---|
| Coinlarni olib, 2 yil ushlab turish | **+33.0%** |
| Strategiya (o'rtacha har savdoda) | **-0.73%** × 649 savdo |

Ya'ni bozor **ko'tarilgan**, strategiya esa zarar keltirgan.

## Nima uchun bu hal qiluvchi

Ilgari savol shunday edi: "strategiyani qanday tuzatamiz". Endi
raqam boshqa savolni qo'yadi:

> Bu strategiya foydalanuvchiga umuman NIMA beradi?

Agar u coinni olib ushlab turishdan yomon ishlasa, unga obuna
sotish — foydalanuvchini zarar ko'radigan yo'lga boshlash demakdir.
Bu 0.4-banddagi halollik talabiga to'g'ridan-to'g'ri zid.

## Mexanizm ham ko'rinib qoldi

    O'rtacha ushlash: 42.9 soat
    Stop masofasi:    ~2.5% (ATR asosida)
    Stop bilan tugash: 62.1%

Ko'tarilayotgan bozorda 42 soatlik pozitsiya va 2.5% lik stop —
bu oddiy kunlik tebranishning ichida. Narx uzoq muddatda o'sadi,
lekin yo'lda har safar stopni yeb ketadi.

Ya'ni strategiya ko'tarilayotgan bozorga QARSHI o'ynaydi: u qisqa
muddatli qaytishlarni ushlamoqchi bo'ladi va uzoq muddatli
o'sishdan chiqib ketadi.

Bu — sozlama xatosi emas, **strategiyaning turi** bilan bog'liq
masala.

## Uch gipoteza va tayanch

| # | Gipoteza | Natija |
|---|---|---|
| 1 | Correction Entry yordam beradi | ❌ |
| 2 | Tuzilmaviy TP2 ehtimolni oshiradi | ❌ teskari |
| 3 | Kirish filtrlari sifatni oshiradi | ❌ win-rate qimirlamadi |
| — | **Tayanch: olib ushlab turish** | **+33% — strategiyadan yaxshi** |

## Cheklovlar (halol o'qish uchun)

- Sinov davri (2024-09 – 2026-09) — asosan KO'TARILUVCHI bozor.
  Tushuvchi bozorda tayanch manfiy bo'lardi va taqqoslash boshqacha
  chiqardi
- Faqat 5 ta yirik coin. Kichik coinlarda natija boshqacha bo'lishi
  mumkin
- "jami%" — foizlar yig'indisi, murakkab foiz emas. Tayanch esa
  bitta pozitsiyaning natijasi. Shkalalar aynan bir xil emas —
  lekin BELGI (musbat/manfiy) shubhasiz

Bu cheklovlar xulosani o'zgartirmaydi: bozor ko'tarilgan, strategiya
zarar ko'rgan.

## Qaror loyiha egasiniki

Texnik jihatdan yana sinash mumkin bo'lgan narsalar bor (masalan
stop kengligi va ushlash muddati). Lekin bu endi "kodni tuzatish"
emas, **mahsulot haqidagi qaror**.
