"""6.2-band: bozor ma'lumotlari qatlami.

  - Binance/Bybit PUBLIC WebSocket orqali narx oqimi (API kalitsiz, bepul)
  - REST orqali tarixiy OHLCV (backtest va indikatorlar uchun)
  - CoinGecko/CoinMarketCap orqali kapitalizatsiya reytingi (3.4-band)

Fail-safe talablari (0.3 va 6.4-band):
  - uzilish va qayta ulanish MAJBURIY log qilinadi
  - `stale_price_seconds` dan eski narx bilan signal BERILMAYDI — buni
    Risk Engine'dagi `FreshDataRule` ta'minlaydi
  - qayta ulanish eksponensial kutish bilan (`reconnect_backoff_seconds`)

HOLAT: 5-bosqichda quriladi.
"""
