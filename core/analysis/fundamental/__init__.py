"""BLOK 1 — Fundamental.

To'rt ichki tekshiruv (2-prompt, 4-qism):

    1.1 Bozor holati    Funding Rate + Open Interest + DXY
    1.2 Pul oqimi       Exchange Netflow + Stablecoin zaxirasi
    1.3 Katalizator     Listing/Delisting + Token Unlock (QATTIQ TO'SIQ)
    1.4 Kayfiyat        Fear & Greed + Sektor + Yangiliklar

MANBALARNING YARMIDA TARIX YO'Q. Bu kod yozilishidan oldin
tekshirildi va `docs/FUNDAMENTAL_MALUMOT_MANBALARI.md` da
jadval bilan yozildi. Qisqasi:

    o'lchanadi     Funding Rate, Fear & Greed
    o'lchanmaydi   Open Interest (30 kun), Netflow (pullik),
                   Sektor (tarix yo'q), Yangiliklar (tarix yo'q)
    jonli-only     Token Unlock / Delisting qattiq to'sig'i

Shuning uchun har bir tekshiruv `MALUMOT_YOQ` qaytara oladi va bu
holat maxrajga KIRMAYDI (`core/analysis/turlar.py`). Aks holda
backtestda 1-blok doim 0/4 chiqib, zanjir hech qachon ulanmasdi.

BOZOR SALOMATLIGI INDEKSI shu blokka SINGDIRILDI (2-prompt, 7-qism):
alohida modul, alohida ON/OFF kalit va "rejim almashish" mantig'i
YOZILMAYDI — eski tizimda aynan o'sha qism rad etilgan edi.
"""

from core.analysis.fundamental.capital_flow import PulOqimi, pul_oqimi
from core.analysis.fundamental.catalyst_watch import Katalizator, katalizator
from core.analysis.fundamental.fundamental_block import FundamentalKirish, fundamental_blok
from core.analysis.fundamental.market_regime import BozorHolati, bozor_holati
from core.analysis.fundamental.sentiment_sector import Kayfiyat, kayfiyat

__all__ = [
    "BozorHolati",
    "FundamentalKirish",
    "Katalizator",
    "Kayfiyat",
    "PulOqimi",
    "bozor_holati",
    "fundamental_blok",
    "katalizator",
    "kayfiyat",
    "pul_oqimi",
]
