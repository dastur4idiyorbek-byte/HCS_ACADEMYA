"""Coin halollik qarorlari reyestri (1.4 va 3.4-band).

Manbalar (yuqoridagi pastdagini bosadi):
  1. `config/default.yaml` dagi boshlang'ich ro'yxat (`seed_*_symbols`)
  2. Bazadagi `coin_rulings` jadvali — admin qo'lda tahrirlaydi

MUHIM tamoyil: shubhali (mashbooh) ham HAROM kabi chetlab o'tiladi —
"shubhali narsadan yiroqlashish". Kod darajasida bu `HalalStatus.is_tradable`
orqali ta'minlanadi: faqat `HALAL` savdoga yaroqli.

3.4-banddagi eslatma: tashqi halollik-skrining xizmatlari (CryptoUmmah, Zoya
Finance, Islamic Finance Guru) ochiq API bermaydi, shuning uchun ro'yxat
ichki yuritiladi va vaqti-vaqti bilan qo'lda solishtiriladi.
"""

from __future__ import annotations

from typing import Protocol

from core.config.schema import HalalScreeningConfig
from core.domain.enums import HalalStatus
from core.domain.models import HalalVerdict

DEFAULT_HALAL_REASON = (
    "Ro'yxatdagi harom yoki shubhali toifalarga kirmaydi: foizli (riba) qarz "
    "berish, qimor/bahs, an'anaviy moliya derivativlari yoki noaniq tabiatli "
    "loyihalar qatoriga qo'shilmagan."
)
DEFAULT_HARAM_REASON = "Harom ro'yxatida (admin tomonidan belgilangan)."
DEFAULT_MASHBOOH_REASON = (
    "Shubhali (mashbooh) ro'yxatida. Shubhali narsa harom kabi chetlab "
    "o'tiladi — shuning uchun savdoga kiritilmaydi."
)
STABLECOIN_REASON = (
    "Stablecoin — narx harakati yo'q, spot savdo strategiyasiga mos emas "
    "(3.4-band filtri)."
)


class RulingRegistry(Protocol):
    """Coin bo'yicha halollik qarorini beruvchi manba."""

    def verdict_for(self, symbol: str) -> HalalVerdict:
        """Berilgan coin uchun qaror. Noma'lum coin — `HALAL` deb qaralmaydi..."""
        ...


class StaticRulingRegistry:
    """Xotiradagi reyestr — konfiguratsiya urug'lari va qo'shimcha qarorlardan.

    Testda va baza ishlamay qolganda (fail-safe) shu ishlatiladi.
    """

    def __init__(
        self,
        haram: dict[str, str] | None = None,
        mashbooh: dict[str, str] | None = None,
        halal: dict[str, str] | None = None,
        stablecoins: set[str] | None = None,
        exclude_stablecoins: bool = True,
    ) -> None:
        self._haram = {k.upper(): v for k, v in (haram or {}).items()}
        self._mashbooh = {k.upper(): v for k, v in (mashbooh or {}).items()}
        self._halal = {k.upper(): v for k, v in (halal or {}).items()}
        self._stablecoins = {s.upper() for s in (stablecoins or set())}
        self._exclude_stablecoins = exclude_stablecoins

    @classmethod
    def from_config(cls, config: HalalScreeningConfig) -> StaticRulingRegistry:
        return cls(
            haram={s: DEFAULT_HARAM_REASON for s in config.seed_haram_symbols},
            mashbooh={s: DEFAULT_MASHBOOH_REASON for s in config.seed_mashbooh_symbols},
            stablecoins=set(config.stablecoin_symbols),
            exclude_stablecoins=config.exclude_stablecoins,
        )

    def verdict_for(self, symbol: str) -> HalalVerdict:
        upper = symbol.upper()

        if self._exclude_stablecoins and upper in self._stablecoins:
            return HalalVerdict(upper, HalalStatus.MASHBOOH, STABLECOIN_REASON)
        if upper in self._haram:
            return HalalVerdict(upper, HalalStatus.HARAM, self._haram[upper])
        if upper in self._mashbooh:
            return HalalVerdict(upper, HalalStatus.MASHBOOH, self._mashbooh[upper])
        if upper in self._halal:
            return HalalVerdict(upper, HalalStatus.HALAL, self._halal[upper])
        return HalalVerdict(upper, HalalStatus.HALAL, DEFAULT_HALAL_REASON)

    # --- admin tahriri (1.4-band) ---

    def set_ruling(self, symbol: str, status: HalalStatus, reason: str) -> None:
        upper = symbol.upper()
        for bucket in (self._haram, self._mashbooh, self._halal):
            bucket.pop(upper, None)
        {
            HalalStatus.HARAM: self._haram,
            HalalStatus.MASHBOOH: self._mashbooh,
            HalalStatus.HALAL: self._halal,
        }[status][upper] = reason

    def merge_overrides(self, overrides: dict[str, HalalVerdict]) -> None:
        """Bazadan kelgan admin qarorlarini ustiga qo'yadi."""
        for verdict in overrides.values():
            self.set_ruling(verdict.symbol, verdict.status, verdict.reason)

    def snapshot(self) -> dict[str, HalalStatus]:
        return {
            **{s: HalalStatus.HARAM for s in self._haram},
            **{s: HalalStatus.MASHBOOH for s in self._mashbooh},
            **{s: HalalStatus.HALAL for s in self._halal},
        }
