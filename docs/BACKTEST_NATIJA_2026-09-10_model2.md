# XGBoost 2-yugurish: kutilayotgan foyda modeli

Sana: 2026-09-10 | Actions: 34469933617
16 486 qator, 51 ustun, 24 halol coin, 4 yil, 4 ta walk-forward oynasi

---

## AVVAL — O'LCHOVNING O'ZIDA XATO TOPILDI

Skript "🟢 Model 4/4 oynada tayanchdan yaxshi" deb chiqardi va
"jonli sinovga tayyorlash" deb tavsiya qildi.

**Bu yolg'on edi.** Xulosa kodi har bir oynaning ENG YAXSHI
chegarasini tanlardi — imtihon natijasini KO'RGANDAN KEYIN:

| oyna | tanlangan chegara | natija |
|---|---|---|
| 1 | kutilgan foyda >= 1.5% | +8.1% |
| 2 | kutilgan foyda >= 0.0% | +102.4% |
| 3 | kutilgan foyda >= 0.0% | -22.0% |
| 4 | kutilgan foyda >= 2.0% | -46.7% |

Har oynada BOSHQA chegara. Jonli savdoda esa chegara OLDINDAN
qo'yiladi va uni keyin o'zgartirib bo'lmaydi. Ya'ni bu natijaga
erishib bo'lmasdi — u faqat qog'ozda mavjud.

Bundan tashqari shart ham noto'g'ri edi: "tayanchdan yaxshi"
deb baholanardi, "foydali" deb emas. Tayanch zarar keltirsa,
undan kamroq zarar keltirish — baribir zarar.

Ikkalasi ham tuzatildi (`scripts/zanjir_model.py`), regressiya
testi shu raqamlar bilan yozildi.

---

## HAQIQIY NATIJA — BIR XIL CHEGARA BARCHA OYNADA

```
konfiguratsiya                   savdo     jami%   musbat oyna  tayanchdan
-------------------------------------------------------------------------------
TAYANCH (hozirgi qoidalar)         162    -169.1           0/4           -
yutadimi >= 0.35                  1832    -795.7           1/4           -
yutadimi >= 0.45                  1269    -550.7           1/4           -
yutadimi >= 0.55                   861    -523.8           0/4           -
yutadimi >= 0.65                   504    -337.7           0/4           -
kutilgan foyda >= 0.0%            1215    -428.7           1/4           -
kutilgan foyda >= 0.5%             392    -296.4           1/4           -
kutilgan foyda >= 1.0%             206    -193.7           1/4           -
kutilgan foyda >= 1.5%             132     -94.8           2/4          ha
kutilgan foyda >= 2.0%              90    -122.0           1/4           -
```

**BITTA HAM KONFIGURATSIYA FOYDA BERMADI.**

Eng yaxshisi — `kutilgan foyda >= 1.5%` — tayanchdan yaxshi
(-94.8% va -169.1%), lekin baribir zarar. Va uning ikkala
musbat oynasi mayda (+8.1%, +7.9%), manfiylari katta
(-43.0%, -67.8%).

Musbat natijalarning deyarli hammasi **2-oynada** to'plangan —
bitta qulay bozor davri. Bu edge emas, bu ob-havo.

---

## USTUNLAR MUHIMLIGI

| ustun | ulush |
|---|---|
| `t_fvg` | 7.75% |
| `blok3_maxraj` | 5.80% |
| `nisbat` | 5.76% |
| `t_pastki_tf` | 4.09% |
| `tp_soni` | 4.01% |
| `t_swing_ketma_ketligi` | 3.90% |
| `t_order_block` | 3.83% |
| `t_qarshi_choch_yoq` | 3.73% |
| `narx_entry_farq_pct` | 3.65% |

Eng muhim ustun ham atigi 7.75% — ya'ni **hech bir omil
ustunlik qilmaydi**. Kuchli signal bo'lganda bitta-ikkita ustun
20-40% oladi. Bu yerda 51 ta ustun deyarli teng bo'lingan —
model tayanadigan narsa topmadi.

### Deyarli ishlatilmaganlar (18 ta)

```
t_liquidity_sweep, blok1_kuch, blok3_otdi, blok4_olchanmadi,
blok2_otdi, blok3_olchanmadi, blok2_olchanmadi, blok1_otdi,
blok1_maxraj, blok1_olchanmadi, t_fundamental_mos, t_fibonacci,
t_bozor_holati, t_alternativ_qayta_sinov, t_alternativ_hajm_sakrashi,
t_pul_oqimi, t_katalizator, t_kayfiyat
```

Bu ro'yxatda **butun 1-blok** (`blok1_*` ning hammasi),
`t_bozor_holati` (Bozor Salomatligi Indeksi) va `t_liquidity_sweep`
(LIT moduli) bor.

---

## XULOSA

Bu — **to'rtinchi mustaqil tasdiq**:

1. Ablatsiya: birorta tekshiruvni olib tashlash natijani
   yaxshilamadi ham, yomonlashtirmadi ham
2. Zanjirsiz backtest PF 0.84 / to'liq zanjir bilan 0.83
3. Chegara supurgisi: R:R ni 1.2 dan 3.0 ga ko'tarish g'alaba
   foizini deyarli aynan mutanosib tushirdi
4. **XGBoost: 16 486 qatorda ham foydali chegara topilmadi**

Ma'lumotimizda kelajak haqida ma'lumot yo'q. Model buni
o'rgana olmadi — chunki o'rganadigan narsa yo'q.

**Keyingi qadam mening tavsiyam emas, loyiha egasining
qarori.** Uchta yo'l bor va uchalasi ham ochiq:

1. **Yangi ma'lumot manbai** — narx va strukturadan tashqarida:
   on-chain oqimlar, birja zaxiralari, yangilik/kayfiyat.
   Hozirgi 51 ustunning HAMMASI narxdan olingan.
2. **Boshqa savol** — "qaysi coin o'sadi" o'rniga "bozor qachon
   xavfli" (kirmaslik signali).
3. **Signalni to'xtatish** — bot hozir ham har 4 soatda signal
   chiqaradi, va o'lchov bo'yicha ular zarar keltiradi.
