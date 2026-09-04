"""Zanjir o'lchov skriptlari uchun umumiy qism.

Uchala skript (backtest, ablatsiya, walk-forward) bir xil ma'lumot
yuklashi va bir xil jadval chizishi kerak — aks holda ularning
natijalarini solishtirib bo'lmaydi.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.backtest.dataset import Dataset
from core.backtest.yuklash import yukla
from core.backtest.zanjir_engine import ZanjirNatijasi
from core.config.loader import load_config
from core.config.schema import AppConfig

HISOBOT_PAPKA = Path("reports")
#: O'LCHOV COINLARI — HALOL SKRININGDAN O'TGAN.
#:
#: 2026-09-04 da topilgan xato: o'lchovlar BNB va XRP bilan
#: yuritilgan edi. Holbuki `config/default.yaml` da BNB — HAROM
#: ro'yxatida, XRP — MASHBOOH ro'yxatida. Ya'ni PF 3.50 raqami
#: bot HECH QACHON signal bermaydigan coinlardagi savdolarni ham
#: o'z ichiga olardi.
#:
#: Bu ro'yxat endi test bilan qulflangan
#: (`test_olchov_coinlari_halol.py`): harom yoki mashbooh
#: ro'yxatidagi coin bu yerga tushsa, test yiqiladi.
#:
#: DIQQAT: bu ro'yxat "halol" degan DINIY hukm emas. U faqat
#: loyihaning o'z skrining ro'yxatiga MOS kelishini bildiradi.
#: Yakuniy hukm — mutaxassis kishining ishi (loyiha qoidasi).
STANDART_COINLAR = ["BTC", "ETH", "SOL", "ADA", "AVAX"]

#: 12 coinlik to'plam — 2026-09-04 gacha bo'lgan o'lchovlar shu
#: hajmda yuritilgan. BNB va XRP o'rniga ETC va FIL qo'yildi,
#: qolgan o'nta o'zgarmadi (natijalarni solishtirish uchun).
OLCHOV_12 = [
    "BTC", "ETH", "SOL", "ADA", "AVAX",
    "LINK", "DOT", "ATOM", "LTC", "NEAR",
    "ETC", "FIL",
]

#: Kengaytirilgan to'plam — savdo sonini oshirish uchun.
#: Hammasi 2021-yildan oldin Binance spotda bo'lgan, ya'ni
#: 4 yillik sinovda to'liq tarixi bor.
OLCHOV_24 = [
    *OLCHOV_12,
    "ALGO", "VET", "XLM", "HBAR", "EOS", "ICP",
    "XTZ", "IOTA", "THETA", "EGLD", "GRT", "BCH",
]

#: Isinish kunlari — struktura va POC uchun tarix kerak.
#: Kunlik timeframeda 200 sham ~ 200 kun.
ISINISH_KUN = 200


def umumiy_argumentlar(tavsif: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=tavsif)
    p.add_argument("--days", type=int, default=730)
    p.add_argument("--symbols", default=",".join(STANDART_COINLAR))
    p.add_argument("--end-date", default=None, help="sinov oynasining oxiri (YYYY-MM-DD)")
    p.add_argument("--offline", action="store_true", help="faqat keshdan o'qish")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("--log-level", default="WARNING")
    # US IP dan `api.binance.com` 451 (huquqiy cheklov) qaytaradi.
    # `data-api.binance.vision` — o'sha ma'lumot, ochiq domen.
    p.add_argument(
        "--base-url",
        default=None,
        help="Binance REST manzilini almashtiradi (GitHub Actions uchun)",
    )
    # NOMZOD CHEGARA. `zanjir_chegara.py` topgan qiymatni BOSHQA
    # o'lchovda (masalan walk-forward) tekshirish uchun.
    #
    # Nima uchun bu kerak: parametr izlash natijasi BITTA oynada
    # topiladi. Uni o'sha oynada maqtash — o'zini aldash. Eski
    # loyihaning eng achchiq saboqi aynan shu edi: izlash natijasi
    # keyingi davrga O'TMAGAN (`OLCHOVLAR_XULOSASI.md` #13).
    #
    # Berilmasa — HECH NARSA o'zgarmaydi (test bilan qulflangan).
    p.add_argument("--stop-eng-kam", type=float, default=None)
    p.add_argument("--tp1-nisbat", type=float, default=None)
    return p


def chegara_qolla(config: AppConfig, argumentlar) -> AppConfig:  # noqa: ANN001
    """Nomzod chegarani qo'llaydi. Bayroqsiz — o'zgarishsiz qaytaradi."""
    stop = getattr(argumentlar, "stop_eng_kam", None)
    nisbat = getattr(argumentlar, "tp1_nisbat", None)
    if stop is None and nisbat is None:
        return config

    ozgarishlar = {}
    if stop is not None:
        ozgarishlar["stop_eng_kam_pct"] = stop
    if nisbat is not None:
        ozgarishlar["tp1_eng_kam_nisbat"] = nisbat

    darajalar = dataclasses.replace(config.zanjir.darajalar, **ozgarishlar)
    return dataclasses.replace(
        config, zanjir=dataclasses.replace(config.zanjir, darajalar=darajalar)
    )


async def malumot_tayyorla(argumentlar) -> tuple[AppConfig, Dataset, list[str]]:  # noqa: ANN001
    """Config va Dataset ni tayyorlaydi."""
    logging.basicConfig(level=getattr(logging, argumentlar.log_level.upper(), logging.WARNING))
    config = load_config()
    if getattr(argumentlar, "base_url", None):
        config = dataclasses.replace(
            config,
            market_data=dataclasses.replace(
                config.market_data, rest_base_url=argumentlar.base_url
            ),
        )
    symbols = [s.strip().upper() for s in argumentlar.symbols.split(",") if s.strip()]
    # BTC nisbiy kuch uchun HAR DOIM kerak, hatto ro'yxatda bo'lmasa ham.
    yuklanadigan = list(dict.fromkeys([*symbols, "BTC"]))

    z = config.zanjir.timeframelar
    timeframelar = sorted({z.asosiy, z.tasdiq})

    until = (
        datetime.fromisoformat(argumentlar.end_date) if argumentlar.end_date else None
    )
    dataset = await yukla(
        config,
        yuklanadigan,
        timeframelar,
        argumentlar.days,
        warmup_days=ISINISH_KUN,
        refresh=argumentlar.refresh,
        offline=argumentlar.offline,
        until=until,
    )
    return chegara_qolla(config, argumentlar), dataset, symbols


@dataclass(frozen=True, slots=True)
class Olchov:
    """Jadval uchun bitta qator."""

    nom: str
    signal: int
    foydali_pct: float
    profit_factor: float
    ortacha_pct: float
    jami_pct: float
    pasayish_pct: float


def olchov_qur(natija: ZanjirNatijasi) -> Olchov:
    return Olchov(
        nom=natija.nom,
        signal=natija.signal_soni,
        foydali_pct=natija.foydali_pct,
        profit_factor=natija.profit_factor,
        ortacha_pct=natija.ortacha_pct,
        jami_pct=natija.jami_pct,
        pasayish_pct=natija.eng_chuqur_pasayish,
    )


def jadval(olchovlar: list[Olchov]) -> str:
    sarlavha = (
        f"{'konfiguratsiya':<34}{'signal':>7}{'foydali':>9}{'PF':>7}"
        f"{'o‘rt.%':>9}{'jami%':>10}{'pasayish':>10}"
    )
    qatorlar = [sarlavha, "-" * len(sarlavha)]
    for o in olchovlar:
        pf = "∞" if o.profit_factor == float("inf") else f"{o.profit_factor:.2f}"
        qatorlar.append(
            f"{o.nom:<34}{o.signal:>7}{o.foydali_pct:>8.1f}%{pf:>7}"
            f"{o.ortacha_pct:>9.2f}{o.jami_pct:>10.1f}{o.pasayish_pct:>9.1f}%"
        )
    return "\n".join(qatorlar)


def csv_saqla(nom: str, olchovlar: list[Olchov]) -> Path:
    HISOBOT_PAPKA.mkdir(parents=True, exist_ok=True)
    yol = HISOBOT_PAPKA / nom
    with yol.open("w", newline="", encoding="utf-8") as f:
        yozuvchi = csv.writer(f)
        yozuvchi.writerow(
            ["konfiguratsiya", "signal", "foydali_pct", "profit_factor",
             "ortacha_pct", "jami_pct", "pasayish_pct"]
        )
        for o in olchovlar:
            yozuvchi.writerow([
                o.nom, o.signal, f"{o.foydali_pct:.2f}", f"{o.profit_factor:.4f}",
                f"{o.ortacha_pct:.4f}", f"{o.jami_pct:.2f}", f"{o.pasayish_pct:.2f}",
            ])
    return yol


def voronka_matni(natija: ZanjirNatijasi) -> str:
    """Zanjir qayerda uzilgani — "nega signal yo'q" savoliga javob."""
    qatorlar = ["   Zanjir qayerda uzildi:"]
    for nom, soni in sorted(natija.uzilishlar.items(), key=lambda x: -x[1]):
        qatorlar.append(f"      {soni:>6} × {nom}")
    if natija.daraja_radlari:
        qatorlar.append("   Zanjir to'liq, lekin daraja rad etildi:")
        for sabab, soni in sorted(natija.daraja_radlari.items(), key=lambda x: -x[1]):
            qatorlar.append(f"      {soni:>6} × {sabab}")
    if natija.sigim_radlari:
        qatorlar.append("   Signal tayyor, lekin PORTFEL chegarasi to'sdi:")
        for sabab, soni in sorted(natija.sigim_radlari.items(), key=lambda x: -x[1]):
            qatorlar.append(f"      {soni:>6} × {sabab}")
    return "\n".join(qatorlar)


#: Tekshiruv shu ulushdan kam ijobiy chiqsa — ZAIF deb belgilanadi.
#:
#: 0.10 raqami TAXMINIY va shundayligicha yozilgan: u qaror
#: qabul qilmaydi, faqat ro'yxatni tartiblaydi. Qaror har doim
#: backtestdan chiqadi.
ZAIF_ULUSH = 0.10


def zaiflik_matni(natija: ZanjirNatijasi) -> str:
    """Qaysi ichki tekshiruv zaif — sizning asl savolingiz.

    Ablatsiya "tekshiruvni olib tashlasa nima bo'ladi" deydi.
    Bu jadval boshqa narsani aytadi: "tekshiruv qanchalik tez-tez
    ijobiy chiqadi". Blok 4 tadan bittasi bilan o'tgani uchun,
    doim YO'Q chiqadigan tekshiruv blokni hech qachon o'tkazmaydi
    — u zaif halqa.

    MA'LUMOT YO'Q alohida ustunda: u "yomon" emas, "sinalmagan".
    Ikkalasini aralashtirish eski tizimning xatosi edi.
    """
    if not natija.tekshiruv_holatlari:
        return "   (tekshiruv holatlari yig'ilmagan)"

    qatorlar = [
        "   Ichki tekshiruvlar — qaysi biri ZAIF:",
        f"      {'tekshiruv':<22}{'ko‘rildi':>9}{'HA':>8}{'YO‘Q':>8}{'ma’lumot yo‘q':>15}",
    ]
    for nom, hisob in sorted(
        natija.tekshiruv_holatlari.items(),
        key=lambda x: -(x[1]["ha"] + x[1]["yoq"] + x[1]["malumot_yoq"]),
    ):
        jami = hisob["ha"] + hisob["yoq"] + hisob["malumot_yoq"]
        olchandi = hisob["ha"] + hisob["yoq"]
        ulush = hisob["ha"] / olchandi if olchandi else 0.0
        belgi = " ⚠️ zaif" if olchandi and ulush < ZAIF_ULUSH else ""
        if not olchandi:
            belgi = " ⚫ umuman o‘lchanmagan"
        qatorlar.append(
            f"      {nom:<22}{jami:>9}{hisob['ha']:>8}{hisob['yoq']:>8}"
            f"{hisob['malumot_yoq']:>15}   {ulush * 100:>5.1f}%{belgi}"
        )
    return "\n".join(qatorlar)
