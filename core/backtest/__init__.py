"""6.3-band: backtest qobiliyati — arxitekturada albatta bo'lishi SHART.

Sabab: strategiya qoidalari va vaznlarini (shu jumladan Bozor Salomatligi
Indeksi formulasi koeffitsientlarini) sozlash uchun zarur. Jonli pulga
qo'yishdan oldin kamida 1-2 yillik tarixiy ma'lumotda sinash MAJBURIY.

Arxitektura buni allaqachon qo'llab-quvvatlaydi:
  - strategiyalar `StrategyInput` dan o'qiydi, tarmoqqa murojaat qilmaydi
  - Risk Engine `RiskContext` dan o'qiydi, jonli holatga bog'lanmagan
  - vaqt `Clock` abstraksiyasi orqali — testda "muzlatiladi"

Shu sababli bir xil kod jonli rejimda ham, backtestda ham ishlaydi.

HOLAT: 16-bosqichda quriladi.
"""
