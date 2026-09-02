# Backtest natijasi #2 — tuzilmaviy TP2 va xarajatlar

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun | 4 380 qadam
**Kod:** `89b2ea9` | GitHub Actions run #5
**Farqi #1 dan:** komissiya va sirg'anish endi hisobga olinadi (0.3%/savdo)

---

## Jadval

```
konfiguratsiya              signal  savdo     win   o'rt.%    jami%  pasayish
-----------------------------------------------------------------------------
eski: formulaviy TP2           667    649     38%    -0.73   -471.6    547.6%
yangi: tuzilmaviy TP2          660    649     38%    -0.98   -634.8    665.1%
tuzilmaviy, nisbat >= 1.5      613    601     38%    -0.91   -544.2    584.1%
tuzilmaviy, nisbat >= 2.0      571    555     38%    -1.01   -560.2    600.0%
nazorat: Correction Entry      671    653     38%    -0.75   -489.6    565.6%
```

| variant | TP2 gacha | profit factor |
|---|---|---|
| eski: formulaviy TP2 | **29.9%** | 0.65 |
| yangi: tuzilmaviy TP2 | 24.7% | 0.56 |
| tuzilmaviy, nisbat >= 1.5 | 23.0% | 0.57 |
| tuzilmaviy, nisbat >= 2.0 | 19.5% | 0.52 |

---

## 1. GIPOTEZA RAD ETILDI

Men shunday deb o'ylagan edim:

> TP2 haqiqiy qarshilik zonasiga qo'yilsa, unga yetish EHTIMOLI
> oshadi (nisbat pasayishi evaziga).

**Bu noto'g'ri chiqdi.** Ehtimol oshmadi, **pasaydi**: 29.9% -> 24.7%.

Sabab oddiy va men uni oldindan ko'rmadim: TP1 dan keyingi haqiqiy
resistance zonasi formuladagi nishondan ko'pincha **UZOQROQ**
turadi, yaqinroq emas. Formula TP2 ni stopdan 1.5 baravar masofaga
qo'yadi; bozordagi keyingi jiddiy qarshilik esa odatda undan
narida bo'ladi.

Ya'ni "TP2 juda uzoq" degan tashxisim to'g'ri edi, lekin taklif
qilgan yechimim TP2 ni yana ham UZOQLASHTIRDI.

`tp2_from_structure` **`false` bo'lib qoladi.**

Nisbat chegarasi (1.5, 2.0) ham yordam bermadi — u faqat signal
sonini qisqartirdi (667 -> 613 -> 571) va TP2 gacha yetishni yana
pasaytirdi (23.0% -> 19.5%).

---

## 2. Xarajat modeli TO'G'RI ulangan

Bu tekshirilishi kerak edi, chunki noto'g'ri ulangan xarajat butun
o'lchovni buzardi.

| | #1 (xarajatsiz) | #2 (xarajatli) | farq |
|---|---|---|---|
| eski yo'l, jami% | -276.9 | -471.6 | **-194.7** |

Kutilgan farq: 649 savdo x 0.3% = **194.7%**. Aynan mos keldi.

Profit factor 0.77 dan 0.65 ga tushdi. Ya'ni "savdo bepul" degan
soddalashtirish tizimni haqiqiydan sezilarli darajada yaxshiroq
ko'rsatib turgan ekan.

---

## 3. Ma'lumot nimani ko'rsatyapti

Beshta variantda TP2 turli joyga qo'yildi, signal soni 571 dan 671
gacha o'zgardi. **Win-rate esa hamma joyda 37.5–38.4%.**

Bu qat'iy barqarorlik bir narsani aytadi:

> Muammo TP da emas. Kirishlarning ~62% i TP ga umuman yaqinlashmay,
> to'g'ri stopga boradi.

TP ni qayerga qo'yish o'sha 62% ga hech qanday ta'sir qilmaydi.
Ikki gipoteza (Correction Entry, tuzilmaviy TP2) rad etildi va
ikkalasi ham TP/kirish YO'LI haqida edi. Endi savol KIRISHNING
O'ZIGA ko'chadi.

---

## 4. Keyingi gipotezalar (kirish sifati)

Bular oldindan yozilgan — natijani ko'rib turib tanlanmagan. Har
birining mexanizm izohi bor:

| Gipoteza | Sozlama | Mexanizm |
|---|---|---|
| Kunlik trend MAJBURIY bo'lsin | `require_htf_alignment: true` | Hozir `false`. Tushayotgan kunlik trendda support zonasi ushlab turmaydi — narx undan o'tib ketadi |
| Indikator tasdig'i majburiy | `require_confirmation: true` | Hozir faqat ballga ta'sir qiladi. Kechikish evaziga soxta kirishlar kamayadi |
| Faqat kuchli trend | `adx_trend_threshold` 20 -> 25 | Tekis bozorda support/resistance ma'nosini yo'qotadi |
| Faqat chuqur Discount | `entry_max_range_pct` 55 -> 40 | Diapazonning pastki qismida stopgacha masofa qisqaroq |

**INTIZOM.** Bu variantlardan eng yaxshisini tanlab "tasdiqlandi"
deyish mumkin emas — to'rtta gipotezadan bittasi tasodifan ham
yaxshi chiqadi. Agar biror variant yaxshi natija bersa, u
BOSHQA DAVRDA qayta tekshirilishi shart (masalan birinchi yilda
tanlab, ikkinchi yilda tasdiqlash).

Bu qoida oldindan yozib qo'yildi, natijani ko'rgandan keyin emas.

---

## 5. Holat

- `correction_entry.enabled` — **false** (natija #1)
- `tp2_from_structure` — **false** (natija #2)
- Jonli pulga qo'yilmaydi
- Ikkita gipoteza rad etildi, uchinchi to'plam sinovga tayyor
