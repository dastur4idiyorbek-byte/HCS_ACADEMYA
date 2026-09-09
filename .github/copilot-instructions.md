# HALOL CRYPTO SAVDO — kod yozish qoidalari

Bu faylni VS Code Copilot HAR BIR so'rovda avtomatik o'qiydi.
Loyihada kod yozayotgan bo'lsang, quyidagilar MAJBURIY.

## Loyiha nima

Halol kripto **spot** savdo signallari: Telegram bot + Next.js sayt,
Railway'da ishlaydi. Faqat **long** (sotib olish). **Leverage yo'q,
futures yo'q, riba yo'q, short yo'q.** Bu texnik tanlov emas —
mahsulotning asosi. Shularni qo'shadigan kod YOZILMAYDI.

## Til

- Kod: Python 3.11 (`core/`, `bot/`, `scripts/`), TypeScript (`web/`).
- **Izohlar, docstring'lar, o'zgaruvchi va funksiya nomlari — o'zbekcha.**
  Mavjud fayllarni ochib ko'r: `bolaklarni_yarat`, `joylashtir`,
  `kutmoqda`, `sabab`. Yangi kod ham shunday bo'lsin.
- Foydalanuvchiga ko'rinadigan matn `web/src/lib/i18n/uz.json` va
  `ru.json` da — **ikkalasiga ham** qo'shiladi, kodga yozilmaydi.

## Izoh yozish uslubi — eng muhim qoida

Izoh **NIMA qilinayotganini emas, NEGA shunday qilinganini** yozadi.
Kod nima qilishini o'zi aytadi.

```python
# YOMON:
# Stopni likvidlik ostiga qo'yamiz
stop = likvidlik * (1 - bufer / 100)

# YAXSHI:
# Stop aynan likvidlik darajasida tursa, bozor o'sha yerdagi
# buyurtmalarni "yig'ib" qaytadi va biz zarar bilan chiqamiz —
# savdo esa aslida to'g'ri edi. Bufer shu uchun.
stop = likvidlik * (1 - bufer / 100)
```

Bir qarorga sabab bo'lgan narsa — savdo mantig'i, o'lchov natijasi,
avval bo'lgan xato — izohda qoladi. Sababi yo'q izoh yozilmaydi.

## Arxitektura — qavatlar

`core/` ichidagi modullar qavatlarga bo'lingan. **Bog'liqlik faqat
pastga qaraydi.** Buni `tests/test_arxitektura.py` mexanik tekshiradi.

```
0: utils, domain, portfolio      <- portfolio HECH NARSAGA bog'lanmaydi
1: config, admin, storage
2: market_data, halal_screening
3: analysis
4: position_sizing, risk_engine, position
5: services
6: backtest
```

Yangi `core/` moduli qo'shsang, `QAVATLAR` ga qatorini yoz.

## Nimaga TEGILMAYDI

- `core/position_sizing/` — loyiha egasining shaxsiy rejasi.
  Aniq so'ralmaguncha o'zgartirilmaydi.
- Bosh sahifadagi diniy iqtibos `[TASDIQLASH KUTILMOQDA]` placeholder
  bo'lib qoladi. **Uni AI o'ylab topmaydi va yozmaydi** — muftiy yoki
  olim tasdiqlashi kerak.
- Saytda alohida to'lov mexanizmi qurilmaydi — to'lov faqat botda.
- Haram/shubhali coinlar ro'yxati — bilimli odam tasdig'iga muhtoj.

## O'lchanmagan raqam qo'shilmaydi

Signal qaroriga ta'sir qiladigan **yangi qat'iy filtr yoki yangi
chegara raqami qo'shilmaydi**, agar backtest bilan o'lchanmagan
bo'lsa. Sabab: har bir tekshirilmagan filtr signal sonini jimgina
nolga tushirishi mumkin.

Kodda yangi raqam paydo bo'lsa (masalan `BUFER_PCT = 0.3`), uni
`docs/GIPOTEZA_DAFTARI.md` ga yozish SHART — aks holda
`tests/test_gipoteza_daftari.py` yiqiladi. Holatlar:

- 🔴 o'lchanmagan
- 🟡 noaniq
- 🟢 gipoteza emas (mexanik/texnik qiymat)
- ⚫ rad etilgan

Yangi mantiq **passiv** bo'lsin: ma'lumot yo'q bo'lsa `None` /
`MALUMOT_YOQ` qaytarsin va qarorga aralashmasin. Taxmin qilmasin.

## Ma'lumot yo'qligi "0" emas

Narx olinmasa `0.0` ko'rsatilmaydi — "ma'lumot olinmadi" deyiladi.
`+$0.00` foydalanuvchini aldaydi.

## Tekshirish — ish tugaganini shu belgilaydi

Python o'zgarsa:

```bash
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pytest -q
```

Sayt o'zgarsa:

```bash
cd web && npm run check && npm run build
```

**Hammasi yashil bo'lmaguncha ish tugagan hisoblanmaydi.**
Test yiqilsa — testni o'chirish yoki bo'shashtirish TAQIQLANADI.
Test nimani himoya qilayotganini tushun, keyin kodni to'g'irla.
Agar test haqiqatan eskirgan bo'lsa, sababini izohda yoz.

- `ruff`: `line-length = 100`, qoidalar `E, F, I, UP, B, SIM`.
- Har bir yangi xatti-harakatga test yoziladi.
- `tests/test_import_qilinadi.py` har bir modulni import qiladi —
  o'chirilgan fayldan qolgan import darrov ushlanadi.

## Git

- Ishlaydigan shox: `claude/assalomu-alaykum-hncsjy`. Boshqa shoxga
  push qilinmaydi.
- Commit xabari o'zbekcha va nima o'zgargani aniq yozilgan bo'lsin.
- So'ralmaguncha Pull Request ochilmaydi.

## Ish hajmi

So'ralgan ishni bajar — ko'p ham emas, kam ham emas. "Bu joyni ham
yaxshilab qo'yay" deb qo'shimcha o'zgarish kiritilmaydi: har bir
qo'shimcha o'zgarish tekshirilishi kerak bo'ladi.
