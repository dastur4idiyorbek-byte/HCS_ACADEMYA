"""Ablation va walk-forward skriptlari uchun UMUMIY qism.

Nima uchun alohida modul. Ikkala yangi skript ham bir xil uch narsani
qiladi: ma'lumot yuklaydi, natijadan bir xil o'lchovlarni oladi, jadval
va CSV yozadi. Ular har birida alohida yozilsa, bir kun jimgina ajralib
ketardi va ikki hisobot boshqa-boshqa narsani o'lchayotgan bo'lardi —
bu loyihada takrorlanuvchi xato turi (`docs/ARXITEKTURA.md`, 68-bo'lim).

MUHIM: bu modul hech qanday QAROR qabul qilmaydi. Ball, vazn, chegara va
strategiya mantig'iga tegilmaydi — u faqat o'lchaydi.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.backtest import BacktestResult, Dataset
from core.config import AppConfig

#: Hisobotlar shu papkaga yoziladi.
HISOBOT_PAPKA = Path("reports")


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #


def umumiy_argumentlar(parser: argparse.ArgumentParser) -> None:
    """`scripts.backtest` bilan BIR XIL ma'lumot bayroqlari."""
    from scripts.backtest import STANDART_COINLAR

    parser.add_argument("--symbols", default=",".join(STANDART_COINLAR))
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--refresh", action="store_true", help="keshni yangilash")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="tarmoqqa chiqmaslik — faqat data/candles/ dagi kesh",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Binance manbai (AQSh serverlarida https://data-api.binance.vision)",
    )
    parser.add_argument(
        "--end-date", default=None, help="sinov oynasining OXIRI (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="tahlil qadamlari soni — tez sinab ko'rish uchun",
    )


async def malumot_tayyorla(
    argumentlar: argparse.Namespace,
) -> tuple[AppConfig, Dataset, list[str], datetime | None]:
    """Konfiguratsiya va ma'lumot to'plamini tayyorlaydi.

    Yuklash mantig'i `scripts.backtest` dan CHAQIRILADI, ko'chirilmaydi:
    kesh nomlari, isinish kunlari va sahifalash bir joyda qolsin.
    """
    import dataclasses

    from core.config import load_config
    from core.utils.logging_setup import setup_logging
    from scripts.backtest import KeshYetishmaydi, _yukla

    setup_logging(level="INFO")
    config = load_config()
    if argumentlar.base_url:
        config = dataclasses.replace(
            config,
            market_data=dataclasses.replace(
                config.market_data, rest_base_url=argumentlar.base_url.rstrip("/")
            ),
        )

    coinlar = [s.strip().upper() for s in argumentlar.symbols.split(",") if s.strip()]

    oxiri: datetime | None = None
    if argumentlar.end_date:
        try:
            oxiri = datetime.fromisoformat(argumentlar.end_date).replace(tzinfo=UTC)
        except ValueError:
            raise SystemExit(
                f"--end-date noto'g'ri: {argumentlar.end_date} (YYYY-MM-DD kutiladi)"
            ) from None

    try:
        dataset = await _yukla(
            config,
            coinlar,
            argumentlar.days,
            argumentlar.refresh,
            offline=argumentlar.offline,
            until=oxiri,
        )
    except KeshYetishmaydi as xato:
        raise SystemExit(str(xato)) from xato

    return config, dataset, coinlar, oxiri


# --------------------------------------------------------------------------- #
#  O'lchov qatori
# --------------------------------------------------------------------------- #

#: CSV va jadvaldagi ustunlar — BITTA manba.
USTUNLAR = ("nom", "izoh", "signal", "foydali_pct", "profit_factor", "ortacha_savdo_pct",
            "jami_pct", "pasayish_pct")


@dataclass(frozen=True, slots=True)
class Olchov:
    """Bitta yugurishning natijasi — hisobot uchun tayyor shakl."""

    nom: str
    izoh: str
    signal: int
    foydali_pct: float | None
    profit_factor: float | None
    ortacha_savdo_pct: float | None
    jami_pct: float
    pasayish_pct: float

    def csv_qatori(self) -> dict[str, object]:
        return {
            "nom": self.nom,
            "izoh": self.izoh,
            "signal": self.signal,
            "foydali_pct": _yumaloq(self.foydali_pct, 1),
            "profit_factor": _yumaloq(self.profit_factor, 2),
            "ortacha_savdo_pct": _yumaloq(self.ortacha_savdo_pct, 2),
            "jami_pct": round(self.jami_pct, 1),
            "pasayish_pct": round(self.pasayish_pct, 1),
        }


def olchov_qur(nom: str, izoh: str, natija: BacktestResult) -> Olchov:
    """`BacktestResult` dan hisobot qatorini yig'adi.

    Komissiya va slippage (yo'l xarajati 0.3%) dvigatelning ICHIDA
    hisoblangan — bu yerda hech narsa qayta hisoblanmaydi.
    """
    return Olchov(
        nom=nom,
        izoh=izoh,
        signal=natija.closed,
        foydali_pct=None if natija.win_rate is None else natija.win_rate * 100,
        profit_factor=natija.profit_factor,
        ortacha_savdo_pct=natija.average_result_pct,
        jami_pct=natija.total_return_pct,
        pasayish_pct=natija.max_drawdown_pct,
    )


def _yumaloq(qiymat: float | None, raqam: int) -> str | float:
    return "" if qiymat is None else round(qiymat, raqam)


# --------------------------------------------------------------------------- #
#  Chiqish
# --------------------------------------------------------------------------- #


def jadval(olchovlar: list[Olchov], birinchi_ustun: str, ikkinchi_ustun: str) -> str:
    """Matnli jadval — terminalda ham, faylda ham bir xil ko'rinadi."""
    sarlavha = (
        birinchi_ustun, ikkinchi_ustun, "signal", "foydali", "PF", "o'rt.%", "jami%",
        "pasayish",
    )
    qatorlar = [
        (
            o.nom,
            o.izoh,
            str(o.signal),
            "—" if o.foydali_pct is None else f"{o.foydali_pct:.1f}%",
            "—" if o.profit_factor is None else f"{o.profit_factor:.2f}",
            "—" if o.ortacha_savdo_pct is None else f"{o.ortacha_savdo_pct:+.2f}",
            f"{o.jami_pct:+.1f}",
            f"{o.pasayish_pct:.1f}%",
        )
        for o in olchovlar
    ]
    kenglik = [
        max([len(sarlavha[i]), *(len(q[i]) for q in qatorlar)])
        for i in range(len(sarlavha))
    ]
    chiziq = "-+-".join("-" * k for k in kenglik)
    satrlar = [
        " | ".join(s.ljust(k) for s, k in zip(sarlavha, kenglik, strict=True)),
        chiziq,
    ]
    satrlar += [
        " | ".join(s.ljust(k) for s, k in zip(q, kenglik, strict=True)) for q in qatorlar
    ]
    return "\n".join(satrlar)


def csv_saqla(fayl: str, olchovlar: list[Olchov]) -> Path:
    """CSV ni `reports/` papkasiga yozadi va yo'lini qaytaradi."""
    HISOBOT_PAPKA.mkdir(parents=True, exist_ok=True)
    yol = HISOBOT_PAPKA / fayl
    with yol.open("w", encoding="utf-8", newline="") as f:
        yozuvchi = csv.DictWriter(f, fieldnames=list(USTUNLAR))
        yozuvchi.writeheader()
        for olchov in olchovlar:
            yozuvchi.writerow(olchov.csv_qatori())
    return yol


def matn_saqla(fayl: str, matn: str) -> Path:
    HISOBOT_PAPKA.mkdir(parents=True, exist_ok=True)
    yol = HISOBOT_PAPKA / fayl
    yol.write_text(matn + "\n", encoding="utf-8")
    return yol


# --------------------------------------------------------------------------- #
#  Dataset kesimi (walk-forward uchun)
# --------------------------------------------------------------------------- #


def kesim(dataset: Dataset, boshi: datetime, oxiri: datetime) -> Dataset:
    """Ma'lumotni vaqt oralig'i bo'yicha kesadi.

    Kesim ICHIDA isinish tarixi ham bo'lishi kerak: dvigatel har doim
    boshidagi `warmup_steps` qadamni tahlilsiz o'tkazadi. Chegaralarni
    `bolaklar()` hisoblaydi — bu funksiya faqat kesadi.
    """
    yangi = Dataset()
    for symbol, seriya in dataset.series.items():
        for tf, shamlar in seriya.candles.items():
            yangi.add(symbol, tf, [c for c in shamlar if boshi <= c.open_time <= oxiri])
    return yangi


@dataclass(frozen=True, slots=True)
class Bolak:
    """Walk-forward bo'lagi: tahlil oynasi + unga tegishli isinish."""

    nomer: int
    tahlil_boshi: datetime
    tahlil_oxiri: datetime
    kesim_boshi: datetime

    @property
    def oraliq(self) -> str:
        return f"{self.tahlil_boshi.date()} .. {self.tahlil_oxiri.date()}"


def bolaklar(config: AppConfig, dataset: Dataset, soni: int) -> list[Bolak]:
    """Tahlil oynasini `soni` ta teng bo'lakka bo'ladi.

    Har bo'lak uchun kesim boshi shunday tanlanadiki, dvigatel o'zining
    isinish qadamlarini o'tkazib bo'lgach AYNAN bo'lak boshida turadi.
    Ya'ni ikkinchi bo'lak birinchisining ma'lumotini isinish sifatida
    ishlatadi, lekin natijaga qo'shmaydi.
    """
    from core.backtest.warmup import warmup_steps

    vaqtlar = dataset.timeline(config.analysis.entry_timeframe)
    isinish = warmup_steps(config)
    tahlil = vaqtlar[isinish:]
    if soni < 2 or len(tahlil) < soni * 2:
        raise SystemExit(
            f"Bo'lish uchun ma'lumot yetarli emas: {len(tahlil)} tahlil qadami, "
            f"{soni} bo'lak so'raldi. `--days` ni oshiring."
        )

    uzunlik = len(tahlil) // soni
    natija: list[Bolak] = []
    for k in range(soni):
        a = k * uzunlik
        b = len(tahlil) if k == soni - 1 else (k + 1) * uzunlik
        natija.append(
            Bolak(
                nomer=k + 1,
                tahlil_boshi=tahlil[a],
                tahlil_oxiri=tahlil[b - 1],
                kesim_boshi=vaqtlar[a],
            )
        )
    return natija
