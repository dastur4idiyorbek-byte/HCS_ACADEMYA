"""3.7-band: Bozor Salomatligi Indeksi — tizimning markaziy pulsi.

Formula (har sham yopilganda qayta hisoblanadi, 0-100):
    BTC Dominance holati (barqarormi, keskin o'zgaryaptimi)
  + Top-30 Halal coinlarning umumiy trend yo'nalishi
  + Volatillik rejimi (ADX)
  + Agregat foydalanuvchi sig'imi (5.2-band — allaqachon tayyor:
    `core.position_sizing.compute_aggregate_capacity`)
  + Faol signallar to'yinganlik darajasi

Natija:
    🟢 80-100 — chegara past (erkin)
    🟡 40-79  — ehtiyotkorroq (chegara balandroq)
    🔴 0-39   — yangi signal to'xtaydi, faqat kuzatuv

Kelajakda yangi omil (masalan Fear & Greed Index) qo'shilsa, formulaga
shunchaki qo'shiladi — butun tizim qayta qurilmaydi. Shuning uchun omillar
`HealthFactor` ro'yxati sifatida modellashtirilgan.

HOLAT: 10-bosqichda quriladi (boshqa modullar tayyor bo'lgandan keyin,
chunki bu ularning natijalarini birlashtiradi).
Chiqadigan tip: `core.domain.models.MarketHealth`.
"""
