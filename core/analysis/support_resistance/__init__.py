"""3.1-band: Support/Resistance zonalarini aniqlash — BIRLAMCHI tahlil.

Tahlil EMA/RSI/MACD'dan emas, aynan shu moduldan boshlanadi. Aniqlanadi:
  - tarixiy narx darajalari (swing high/low pivotlar)
  - ko'p marta test qilingan zonalar (`min_touches`)
  - Fibonacci 38.2% / 50% / 61.8% — YORDAMCHI sifatida, mustaqil emas
  - yaqin darajalar ATR asosida zonaga birlashtiriladi (nuqta emas, oraliq)

HOLAT: 6-bosqichda quriladi (7-bo'limdagi tartib bo'yicha).
Chiqadigan tip: `core.domain.models.SRZone`.
"""
