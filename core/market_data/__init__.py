"""6.2-band: bozor ma'lumotlari qatlami.

  - Binance PUBLIC WebSocket orqali narx oqimi (API kalitsiz, bepul)
  - REST orqali tarixiy OHLCV (backtest va indikatorlar uchun)
  - CoinMarketCap orqali kapitalizatsiya reytingi (3.4-band)

Fail-safe (0.3 va 6.4-band):
  - uzilish va qayta ulanish MAJBURIY log qilinadi
  - `stale_price_seconds` dan eski narx bilan signal BERILMAYDI — buni
    Risk Engine'dagi `FreshDataRule` ta'minlaydi
  - buzuq xabar butun oqimni to'xtatmaydi
"""

from core.market_data.base import (
    BackoffPolicy,
    CandleProvider,
    PriceCache,
    PriceStream,
    RankingProvider,
    SpikeDetector,
)
from core.market_data.binance import (
    BinanceCandleProvider,
    BinancePriceStream,
    from_binance_symbol,
    to_binance_symbol,
)
from core.market_data.dominance import CoinMarketCapDominance, DominanceSnapshot
from core.market_data.ranking import (
    CoinGeckoRanking,
    CoinMarketCapRanking,
    FallbackRanking,
    RankingUnavailableError,
    build_ranking_provider,
)

__all__ = [
    "CoinMarketCapDominance",
    "DominanceSnapshot",
    "BackoffPolicy",
    "BinanceCandleProvider",
    "BinancePriceStream",
    "CandleProvider",
    "CoinGeckoRanking",
    "CoinMarketCapRanking",
    "FallbackRanking",
    "RankingUnavailableError",
    "PriceCache",
    "PriceStream",
    "RankingProvider",
    "SpikeDetector",
    "build_ranking_provider",
    "from_binance_symbol",
    "to_binance_symbol",
]
