# XGBoost yo'nalishi — reja va QAT'IY QOIDALAR

Sana: 2026-09-10 | Taklif: loyiha egasi

---

## 1. Nima uchun bu g'oya to'g'ri

Bizning ablatsiya har bir tekshiruvni **birma-bir** o'chirib
ko'radi. Ya'ni u faqat "bu tekshiruv yolg'iz o'zi ishlaydimi"
degan savolga javob beradi.

XGBoost esa **birikmalarni** topadi:

    "Struktura tekshiruvi FAQAT BTC ko'tarilayotganda ishlaydi"
    "Zona sifati FAQAT diapazon tor bo'lganda ma'no beradi"

Bunday shartlar hech qachon o'lchanmagan. Bu — haqiqatan yangi
ma'lumot beradigan yagona yo'nalish.

Va u LLM dan farqli o'laroq **halol backtest qilinadi**: XGBoost
faqat bizning ustunlarni ko'radi, u yangiliklarni o'qimagan va
kelajakni bilmaydi.

---

## 2. Uchta o'lim — ansiz natija yolg'on chiqadi

### 2.1 Kam namuna

Hozirgi zanjir 730 kunda 66 savdo beradi. XGBoost 30+ ustun bilan
66 qatorda **shovqinni yodlab oladi** va chiroyli backtest chiqaradi.

Yechim: dataset zanjir filtridan O'TMAGAN nomzodlarni ham oladi.
Zanjirning o'z natijasi — ustun, filtr emas. Va davr uzaytiriladi
(4 yil), coinlar ko'paytiriladi (24 ta).

**Birinchi qadam aynan shuni tekshiradi: nechta qator chiqadi?**

### 2.2 Kelajakka qarash (lookahead)

Har bir qator faqat o'sha paytgacha mavjud shamlardan quriladi
(`core/backtest/dataset.py` buni majburlaydi).

Yakuni ma'lumot oxiridan keyinga tushadigan nomzodlar butunlay
TASHLANADI — ularning yorlig'i noma'lum va "yutqazdi" deb yozish
modelga yolg'on o'rgatardi.

### 2.3 Walk-forward, tasodifiy bo'lish EMAS

Vaqt qatorida tasodifiy `train/test` bo'lish — eng keng tarqalgan
xato. Model kelasi haftani o'tgan haftadan o'rganib qo'yadi.

Bo'lish DOIM vaqt bo'yicha: 1-2 yil o'rgatish -> keyingi 6 oy
sinov -> oldinga surish. Model HAR BIR oynada tayanchdan yaxshi
bo'lishi kerak, o'rtacha hisobda emas.

---

## 3. Bosqichlar

| # | Nima | Holat |
|---|---|---|
| 1 | Dataset yig'ish (CSV) | ✅ `scripts/zanjir_dataset.py` |
| 2 | Qatorlar sonini ko'rish | ⏳ Actions da yugurtiriladi |
| 3 | Model o'rgatish + walk-forward | ⏸ 2-qadamdan keyin |
| 4 | Ustunlar muhimligi hisoboti | ⏸ |
| 5 | Tayanch bilan solishtirish | ⏸ |

**3-qadamga faqat 2-qadam yetarli qator bersa o'tiladi.**
Taxminan 10 000+ qator kerak. Kam bo'lsa — davr va coinlar
kengaytiriladi, model o'rgatilmaydi.

---

## 4. Kutubxona masalasi — hal qilingan

`requirements.txt` da numpy/pandas ATAYLAB yo'q (arxitektura
qarori, ~100 MB). XGBoost esa numpy talab qiladi.

Yechim:

    O'RGATISH   — faqat GitHub Actions da, alohida
                  `requirements-ml.txt` bilan
    BASHORAT    — o'rgatilgan model JSON ga eksport qilinadi va
                  jonli tizim uni SOF PYTHON bilan o'qiydi
                  (daraxtlar — oddiy if-else shartlar)

Ya'ni serverga numpy KIRMAYDI. Arxitektura qoidasi buzilmaydi.

---

## 5. Nima VA'DA QILINMAYDI

XGBoost ma'lumotda **bo'lmagan** ustunlikni yarata olmaydi. Agar
bizning ustunlarimizda kelajak haqida ma'lumot yo'q bo'lsa, model
ham topa olmaydi.

Ehtimoliy uchta yakun:

1. Model tayanchdan sezilarli yaxshi -> yo'nalish bor;
2. Model tayanch bilan bir xil -> ustunlarimizda ma'lumot yo'q,
   **yangi ma'lumot manbai kerak** (fundamental, on-chain, yangilik);
3. Model o'rgatishda zo'r, sinovda yomon -> haddan tashqari
   moslashish, natija bekor qilinadi.

Uchalasi ham FOYDALI javob. Eng yomoni — javobsiz qolish.
