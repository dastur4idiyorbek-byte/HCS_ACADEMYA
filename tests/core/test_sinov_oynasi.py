"""Backtest sinov OYNASINI tanlay olsin.

MUAMMO. Backtest faqat "oxirgi N kun" ni ko'rardi. Ya'ni har
qanday o'lchov doim BITTA davrda bajarilardi va loyihaning o'z
intizomi — "yaxshi natija BOSHQA DAVRDA qayta tekshirilishi shart"
(`scripts/backtest.py`) — texnik jihatdan bajarib bo'lmaydigan
talab edi. TP1 nisbat polining natijasi (`docs/
BACKTEST_NATIJA_2026-09-02_8.md`) shu sababdan 🔴 bo'lib qoldi:
sakkizta urinishdan birinchisi ishladi, lekin uni tasdiqlashning
yo'li yo'q edi.

Bu yerda ikki narsa qo'riqlanadi:

  1. `until` berilsa, so'rov haqiqatan o'sha paytgacha bo'lgan
     tarixni oladi (va o'tmishdagi sham "yopilmagan" deb
     belgilanmaydi);
  2. har oynaning KESHI alohida — aks holda ikkita "mustaqil"
     o'lchov jimgina bir xil ma'lumotda bajarilardi va takroriy
     tekshiruvning butun ma'nosi yo'qolardi.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.core.test_market_data import SoxtaKlinesSessiyasi, _provayder

OYNA = datetime(2025, 9, 2, tzinfo=UTC)


# --------------------------------------------------------------------------- #
#  Provayder oynani hurmat qiladi
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_oyna_berilsa_sorov_osha_paytgacha_boradi() -> None:
    sessiya = SoxtaKlinesSessiyasi(jami=5000)
    provider = _provayder(sessiya)

    shamlar = await provider.fetch_candles("BTC", "4h", 200, until=OYNA)

    assert sessiya.sorovlar[0]["endTime"] == int(OYNA.timestamp() * 1000)
    assert shamlar, "oyna ichida sham bo'lishi kerak"
    assert shamlar[-1].open_time <= OYNA, "oynadan keyingi sham kirmasin"


@pytest.mark.asyncio
async def test_oyna_ichidagi_songgi_sham_yopilgan_hisoblanadi() -> None:
    """O'tmishdagi sham allaqachon yopilgan.

    "Eng so'nggi sham yopilmagan bo'lishi mumkin" qoidasi faqat
    JONLI so'rovga tegishli. Oyna oxiri o'tmishda bo'lsa ham shu
    qoida qo'llanilsa, backtest o'z sinov oynasining oxirgi shamini
    yarim shakllangan deb hisoblardi.
    """
    provider = _provayder(SoxtaKlinesSessiyasi(jami=5000))

    shamlar = await provider.fetch_candles("BTC", "4h", 200, until=OYNA)

    assert all(s.closed for s in shamlar)


@pytest.mark.asyncio
async def test_oynasiz_sorov_jonli_yolni_ozgartirmaydi() -> None:
    sessiya = SoxtaKlinesSessiyasi(jami=5000)
    provider = _provayder(sessiya)

    shamlar = await provider.fetch_candles("BTC", "4h", 200)

    assert "endTime" not in sessiya.sorovlar[0]
    assert not shamlar[-1].closed


# --------------------------------------------------------------------------- #
#  Ikki oyna bitta keshni bo'lishmaydi
# --------------------------------------------------------------------------- #


def test_har_oynaning_keshi_alohida() -> None:
    from scripts.backtest import _kesh_yoli

    yollar = {
        _kesh_yoli("BTC", "4h"),
        _kesh_yoli("BTC", "4h", "2025-09-02"),
        _kesh_yoli("BTC", "4h", "2026-09-02"),
    }

    assert len(yollar) == 3, (
        "oyna kesh nomiga kirmasa, 2025-yilgi shamlar 2026-yilgi "
        "yugurishda jimgina qayta ishlatilardi"
    )


def test_offline_rejim_ham_oynani_hisobga_oladi() -> None:
    """Offline rejim yetishmagan faylni AYNAN oyna bilan so'rasin."""
    from scripts.backtest import KeshYetishmaydi, _keshdan_yigish

    with pytest.raises(KeshYetishmaydi) as xato:
        _keshdan_yigish(["ZZZYOQCOIN"], ["4h"], "2025-09-02")

    assert "2025-09-02" in str(xato.value)
