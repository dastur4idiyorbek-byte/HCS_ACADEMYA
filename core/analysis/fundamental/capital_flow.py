"""1.2 — Pul oqimi: Exchange Netflow + Stablecoin zaxirasi.

QOIDA (2-prompt): ikkalasi yoki bittasi mos bo'lsa — ✅.

MANBA HOLATI (`docs/FUNDAMENTAL_MALUMOT_MANBALARI.md`):
  Netflow      — pullik (CryptoQuant/Glassnode). Backtestda YO'Q.
  Stablecoin   — CoinGecko bepul planida ~365 kun. Yarim.

Ya'ni bu tekshiruv backtestda ko'pincha `MALUMOT_YOQ` qaytaradi.
Bu — nuqson emas, HALOL holat: o'lchanmagan narsa o'lchandi deb
ko'rsatilmaydi.

YO'NALISH MANTIQI (long uchun):
  netflow MANFIY  = birjadan pul CHIQYAPTI = coinlar hamyonlarga
                    ko'chirilyapti = sotishga tayyor emas -> ijobiy
  stablecoin O'SDI = chetda kutayotgan pul ko'paydi = xarid
                    quvvati bor -> ijobiy
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.turlar import Tekshiruv, ha, malumot_yoq, yoq

#: Netflow shu qiymatdan manfiy bo'lsa — sezilarli chiqish.
#: 🔴 O'LCHANMAGAN — 0 atrofidagi shovqinni kesish uchun.
NETFLOW_CHEGARA_USD = 0.0

#: Stablecoin zaxirasi 7 kunda shu foizdan ko'p o'ssa — ijobiy.
#: 🔴 O'LCHANMAGAN.
STABLECOIN_OSISH_PCT = 0.5


@dataclass(frozen=True, slots=True)
class PulOqimi:
    """1.2 uchun xom ma'lumot."""

    #: Birjaga sof kirim (USD). Manfiy — chiqim.
    netflow_usd: float | None = None
    #: Stablecoin umumiy kapitalizatsiyasining 7 kunlik o'zgarishi, %
    stablecoin_ozgarish_pct: float | None = None


def pul_oqimi(malumot: PulOqimi) -> Tekshiruv:
    """Ikkitadan KAMIDA BITTASI mos bo'lsa ✅ (promptdagi qoida)."""
    ovozlar: list[bool] = []
    sabablar: list[str] = []

    if malumot.netflow_usd is not None:
        mos = malumot.netflow_usd < NETFLOW_CHEGARA_USD
        ovozlar.append(mos)
        sabablar.append(f"netflow {malumot.netflow_usd:+,.0f}$")

    if malumot.stablecoin_ozgarish_pct is not None:
        mos = malumot.stablecoin_ozgarish_pct >= STABLECOIN_OSISH_PCT
        ovozlar.append(mos)
        sabablar.append(f"stablecoin {malumot.stablecoin_ozgarish_pct:+.2f}%")

    if not ovozlar:
        return malumot_yoq("pul_oqimi", "netflow/stablecoin — hech biri yo'q")

    izoh = f"{sum(ovozlar)}/{len(ovozlar)} mos ({', '.join(sabablar)})"
    return ha("pul_oqimi", izoh) if any(ovozlar) else yoq("pul_oqimi", izoh)
