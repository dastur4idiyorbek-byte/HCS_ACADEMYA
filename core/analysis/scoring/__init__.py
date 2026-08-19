"""3.5-band: ball (score) va reyting tizimi.

Vaznlar `config/default.yaml` -> `scoring.weights` da (jami 100):
  S/R zonasi sifati 25 | Trend kuchi 20 | RSI 15 | Hajm 15 | MACD 10 | R/R 15

S/R eng yuqori vaznga ega — 3.1-bandga mos. Aniq raqamlar backtest
jarayonida moslashtiriladi, lekin STRUKTURA (S/R birinchi) o'zgarmaydi.

Har bir omil DARAJALI (graduated) baholanadi, "bor/yo'q" emas.
Minimal ball chegarasi statik EMAS — `RiskEngine.score_threshold()` orqali
Bozor Salomatligi Indeksiga qarab moslashadi.

HOLAT: 8-bosqichda backtest bilan birga quriladi.
Chiqadigan tip: `core.domain.models.ScoreBreakdown`.
"""
