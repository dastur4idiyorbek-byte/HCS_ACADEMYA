"""3.8-band: Signal Xotirasi — o'z-o'zini tekshiruvchi qism (Self-Audit Loop).

Har bir yopilgan signal statistikaga qo'shilib qolmaydi — tizim orqaga qarab
"nima uchun shunday bo'ldi" tahlil qiladi:
  - Stop yegan bo'lsa: S/R zonasi noto'g'ri belgilanganmi? Hajm yolg'on
    signal berganmi? Bozor Salomatligi past bo'lsa ham signal o'tib ketganmi?
  - TP2'gacha yetgan bo'lsa: qaysi omillar eng kuchli ishladi?

Bu — statistika emas, NAQSH (pattern) izlash.

MUHIM: xulosalar AVTOMATIK O'ZGARTIRISH QILMAYDI (xavfli bo'lardi) — faqat
adminga aniq tavsiya sifatida ko'rsatiladi.

Kuzatiladigan alohida holatlar:
  - "Yolg'on signal": faol bo'lgach 1 soat ichida Stop (zaif kirish nuqtasi)
  - Ketma-ket zarar: N ta ketma-ket Stop -> kill switch (Risk Engine'da
    `ConsecutiveLossRule` sifatida allaqachon tayyor)

Chiqadigan natija: haftalik "O'z-o'zini tekshirish hisoboti" (faqat admin).

HOLAT: 13-bosqichda quriladi. Kerakli ma'lumot bazada allaqachon
saqlanmoqda: `signals.market_health_at_entry`, `signals.is_false_signal`,
`signal_events`, `market_health_log`.
"""
