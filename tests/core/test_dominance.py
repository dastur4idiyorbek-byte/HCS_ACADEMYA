"""3.7-band 1-omil: BTC Dominance manbai.

Bu omil indeksning 20 bali. Jonli botda u `None` deb qotirib qo'yilgandi
(`TODO(17)`), ya'ni indeks hech qachon 80 dan oshmasdi va yangi signal
uchun chegara (40) bilan birga tizim doim jim turardi.

Tarmoq bu muhitda yopiq, shuning uchun javob TAHLILI sinaladi: CMC
maydon nomini o'zgartirsa yoki bermasa ham bot yiqilmasligi kerak.
"""

from __future__ import annotations

import pytest

from core.config import load_config
from core.market_data.dominance import CoinMarketCapDominance, _parse


def test_toliq_javob_oqiladi() -> None:
    natija = _parse(
        {"data": {"btc_dominance": 54.2, "btc_dominance_24h_percentage_change": -0.8}}
    )

    assert natija.value == pytest.approx(54.2)
    assert natija.change_24h == pytest.approx(-0.8)


def test_ozgarish_bolmasa_dominance_baribir_olinadi() -> None:
    """CMC bu maydonni har doim ham bermaydi — omil buni hisobga oladi."""
    natija = _parse({"data": {"btc_dominance": 54.2}})

    assert natija.value == pytest.approx(54.2)
    assert natija.change_24h is None


def test_muqobil_maydon_nomi_ham_qabul_qilinadi() -> None:
    natija = _parse({"data": {"btc_dominance": 50.0, "btc_dominance_24h_change": 1.5}})

    assert natija.change_24h == pytest.approx(1.5)


@pytest.mark.parametrize(
    "javob",
    [
        {},
        {"data": None},
        {"data": {}},
        {"data": {"btc_dominance": "ellik"}},
        {"xato": "kalit yaroqsiz"},
    ],
)
def test_buzuq_javob_yiqilmaydi(javob) -> None:  # noqa: ANN001
    """0.3-band: noaniqlikda `None`, istisno emas."""
    assert _parse(javob) is None


async def test_kalitsiz_sorov_yuborilmaydi() -> None:
    """Kalit yo'q bo'lsa tarmoqqa umuman chiqilmaydi."""
    manba = CoinMarketCapDominance(load_config().market_data, api_key="")

    assert not manba.is_configured
    assert await manba.fetch() is None
