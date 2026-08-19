"""3.1-band: indikatorlar — S/R zonasini TASDIQLOVCHI qatlam.

MUHIM: bu modul mustaqil signal manbai EMAS. U faqat "narx muhim S/R
zonasida" degan holat aniqlangandan keyin chaqiriladi va zonani
tasdiqlaydimi yoki yo'qmi degan savolga javob beradi.

Rejalashtirilgan indikatorlar:
  - Trend:            EMA50, EMA200 (narx ikkalasidan yuqori, EMA50 > EMA200)
  - Kirish tasdig'i:  RSI(14) 30dan qaytish; MACD(12/26/9) kesib o'tish
  - Hajm tasdig'i:    oxirgi 20 sham o'rtachasidan yuqori
  - Stop/TP asosi:    ATR(14)
  - Bozor rejimi:     ADX(14) — tekis bozorni ajratish uchun

HOLAT: 7-bosqichda quriladi.
"""
