# Tahlil moduli — barcha o'lchovlar xulosasi

Bitta varaqda: nima sinaldi, nima chiqdi, qaror nima.
Hammasi BTC/ETH/SOL/BNB/XRP, 4 soatlik, 730 kun, xarajat 0.3%/savdo
(#2 dan boshlab). Tayanch — coinni olib ushlab turish: **+31.5%**.

**PF** = profit factor. 1.0 dan past = zarar. 15 o'lchovda birorta
konfiguratsiya tayanchdan yaxshi ishlamadi.

---

## Jadval

| № | Nima sinaldi | Asosiy raqam | Qaror |
|---|---|---|---|
| 1 | Correction Entry strategiyasi | 667 -> 671 signal (+4), jami −276.9 -> −293.7 | ⚫ RAD |
| 2 | Tuzilmaviy TP2 (+ xarajat modeli) | TP2 gacha 29.9% -> 24.7%, PF 0.65 -> 0.56 | ⚫ RAD |
| 3 | Kirish sifati filtrlari (4 xil) | o'rt. −0.73 -> −0.65, lekin savdo 649 -> 431 | ⚫ RAD |
| 4 | TAYANCH o'lchandi | olib ushlash +33.0% / strategiya −0.73% × 649 | 🔴 HAL QILUVCHI |
| 5 | ADX timeframe xatosi tuzatildi | signal 667 -> 389, o'rt. −0.73 -> −1.04 | 🟡 O'LCHOV TUZALDI |
| 6 | Isinish davri tuzatildi (nolinchi nuqta) | signal 389 -> 884, PF 0.64, o'rt. −0.75 | 🟡 O'LCHOV TUZALDI |
| 7 | To'rtta mexanizm (darvoza, TP soni, muddat) | bitta TP PF 0.74 vs oraliqlar 0.64; muddat rad | 🟡 QISMAN |
| 8 | **TP1 nisbat poli 1.5 / 2.0** | **PF 0.30 -> 0.79 / 0.82; o'rt. −1.31 -> −0.51** | 🟢 ISHLADI |
| 9 | Shu poli BOSHQA oynada (2022-2024) | **PF 1.01, jami +15.7%** — takrorlandi | 🟢 YOQILDI |
| 10 | Yakuniy nishon nisbati 2.2 / 2.5 / 3.0 / 4.0 | 0.83 -> 0.78 -> 0.69 -> 0.70 -> 0.64 | ⚫ RAD |
| 11 | Bozor rejimi + zona oynasi + skalp | rejim PF 0.84 -> 0.75; skalpsiz to'g'ri | ⚫ RAD |
| 12 | "Narx harakati" kitob usuli | bitta savdoda **aynan bir xil −0.46%**, win 28.9% -> 21.3% | ⚫ RAD |
| 13 | Ablation + walk-forward | 100 balldan 60 tasi PF ni 0.00-0.03 o'zgartiradi | 🔴 TASHXIS |
| 14 | Audit 2-bosqichi (voronka to'ldi) | 603 -> 593 signal, PF 0.84 o'zgarmadi | 🔴 TASHXIS |
| 15 | Audit 3-bosqichi (uchta yarim holat) | TP1 poli o'chirilsa PF 0.84 -> **0.32** | 🟢 AUDIT AGDARILDI |
| 16 | Surilgan Stop + kamroq savdo + sig'im | PF 0.84 -> 0.36 / 0.15 / 0.72 | ⚫ RAD -> TO'XTASH |

---

## Uch qatorlik xulosa

**1. Faqat BITTA narsa ishladi.** O'n oltita to'plamda yagona
yaxshilanish — TP1 nishoniga nisbat poli: PF 0.30 -> 0.84. U ikkita
kesishmaydigan oynada takrorlandi. Qolgan hamma narsa nolga teng
yoki zarar.

**2. Kirish tanlovini o'zgartirib bo'lmadi.** Sakkizta g'oya sinaldi.
Eng aniq dalil #12 da: ikkita BUTUNLAY BOSHQA kirish mexanizmi
(arzon zona va yorilish-qayta sinov) aynan bir xil natija berdi —
−0.46% har savdoda. Ya'ni muammo qaysi qoidani tanlashda emas.

**3. Ball tizimining uchdan ikkisi ishlamaydi.** Ablation (#13):
trend, RSI, hajm va MACD — jami 100 balldan 60 tasi — olib
tashlansa PF 0.00-0.03 o'zgaradi. Ma'lumot faqat S/R zonasi (−0.04)
va Risk/Reward (−0.07) da.

---

## Nima uchun to'xtatildi

O'lchovlar quruq raqam sifatida uchta narsani ko'rsatdi:

    tayanch (hech narsa qilmaslik)   +31.5%
    eng yaxshi konfiguratsiya        PF 0.84, har savdoda −0.45%
    walk-forward (vaqt bo'yicha)     PF 1.00 -> 0.84 -> 0.69

Uchinchi qator eng muhimi: natija vaqt o'tishi bilan yomonlashadi.
Ya'ni "yaxshi" ko'ringan sozlama o'tmishga moslashgan, kelajakka
emas.

9-to'plam yugurishidan OLDIN to'xtash qoidasi yozildi: hech bir
variant PF 1.0 ga yetmasa, foyda ortidan quvish to'xtaydi. Hech
biri yetmadi (eng yaxshisi — o'zgartirilmagan 0.84).

Signal moduli o'chirilmaydi va "yaxshilanmaydi" — u bor holicha,
ochiq statistika bilan qoladi.

---

---

## ESKI TIZIM YOPILDI — 2026-09-03

Yuqoridagi 16 o'lchov ESKI, 100 balllik tahlil moduliga tegishli.
O'sha modul 2026-09-03 da butunlay o'chirildi
(`docs/OCHIRISH_ROYXATI.md`) va o'rniga to'rt blokli zanjir
qurildi (`docs/YANGI_TAHLIL_MODULI.md`).

**Bu jadval TARIX sifatida qoladi va hech qachon o'chirilmaydi.**
Sabab: yangi tizimda "yana bitta narsa qo'shaylik" degan taklif
kelganda, javob shu yerda turibdi — o'n oltita urinishdan bittasi
ishlagan.

### Yangi tizimga KO'CHIRILGAN uchta saboq

| Saboq | Qayerdan | Yangi tizimda qanday |
|---|---|---|
| TP1/Stop poli ishlaydi | #8, #9 (PF 0.30 → 0.84) | `darajalar.tp1_eng_kam_nisbat` — pol SAQLANDI |
| Surilgan Stop zarar keltiradi | #16 (PF 0.84 → 0.36) | `trailing_yoqilgan: false`, faqat TP2 dan keyin |
| Ball tizimining 60% i bo'sh | #13 (ablatsiya) | Ball YO'Q — zanjir, va ablatsiya MAJBURIY |

### Yangi tizimning o'lchovlari QAYERDA bo'ladi

Yangi natijalar shu faylga QO'SHILMAYDI — ular alohida boshlanadi
(`BACKTEST_NATIJA_2026-09-XX_zanjir.md`). Ikkalasini aralashtirish
xato bo'lardi: eski raqamlar boshqa arxitekturaga tegishli va
ularni yangisi bilan solishtirib bo'lmaydi.

Yagona solishtiriladigan raqam — **tayanch**: coinni olib ushlab
turish (+31.5%). U ikkala tizim uchun ham bir xil savol beradi:
"bu strategiya hech narsa qilmaslikdan yaxshiroqmi?"

---

## To'liq hujjatlar

    #1-#9    docs/BACKTEST_NATIJA_2026-09-02*.md
    #11-#13  docs/BACKTEST_NATIJA_2026-09-03*.md
    #10, #14, #15, #16   docs/GIPOTEZA_DAFTARI.md
