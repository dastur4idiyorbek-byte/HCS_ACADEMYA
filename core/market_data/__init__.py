"""6.2-band: bozor ma'lumotlari qatlami.

  - Binance PUBLIC WebSocket orqali narx oqimi (API kalitsiz, bepul)
  - REST orqali tarixiy OHLCV (backtest va indikatorlar uchun)
  - Bitget — IKKINCHI manba: Binance'da yo'q coinlar uchun va bitta
    birjaning tasodifiy "wick"ini rad etish uchun

2026-09-04: CoinMarketCap provayderlari (reyting va BTC dominance)
O'CHIRILDI. Ular FAQAT eski tahlil moduli uchun qurilgan edi: reyting
"Top-N coin" ro'yxatini yasardi, dominance esa Bozor Salomatligi
Indeksiga kirardi. Ikkalasi ham eski modul bilan birga ketdi.

Yangi modul coinlarni reytingdan olmaydi — ular `config` dagi ANIQ
ro'yxat (`zanjir.kuzatiladigan_coinlar`). Shuning uchun bu yerda
hech qanday API kaliti kerak emas.

Fail-safe (0.3 va 6.4-band):
  - uzilish va qayta ulanish MAJBURIY log qilinadi
  - buzuq xabar butun oqimni to'xtatmaydi
"""

from core.market_data.base import (
    BackoffPolicy,
    CandleProvider,
    PriceCache,
    PriceStream,
    SpikeDetector,
)
from core.market_data.binance import (
    BinanceCandleProvider,
    BinancePriceStream,
    from_binance_symbol,
    to_binance_symbol,
)
from core.market_data.bitget import BitgetCandleProvider, to_bitget_symbol
from core.market_data.price_reconciliation import (
    Solishtiruv,
    qamrov_pct,
    shubhali_vaqtlar,
    solishtir,
)

__all__ = [
    "BackoffPolicy",
    "BinanceCandleProvider",
    "BinancePriceStream",
    "BitgetCandleProvider",
    "CandleProvider",
    "PriceCache",
    "PriceStream",
    "Solishtiruv",
    "SpikeDetector",
    "from_binance_symbol",
    "qamrov_pct",
    "shubhali_vaqtlar",
    "solishtir",
    "to_binance_symbol",
    "to_bitget_symbol",
]
