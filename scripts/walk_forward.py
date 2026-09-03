"""WALK-FORWARD — sozlama tanlangan davrdan TASHQARIDA ham ishlaydimi.

    python -m scripts.walk_forward --days 730 --bolaklar 3
    python -m scripts.walk_forward --days 730 --grid toliq --offline

SAVOL. Backtestda sozlama tanlash oson: o'nlab variant sinaladi va eng
yaxshisi olinadi. Lekin "eng yaxshi" ko'pincha O'SHA DAVRGA moslashib
qolgan bo'ladi (overfitting) va keyingi davrda yiqiladi. Bu skript
aynan shuni tekshiradi.

USUL.

    1. Tarix teng bo'laklarga bo'linadi (standart: 3 ta).
    2. Har bir bo'lakda parametr to'ri sinaladi va PF bo'yicha ENG
       YAXSHISI tanlanadi — bu O'RGATISH bo'lagi.
    3. O'sha tanlov KEYINGI bo'lakda, HECH NARSA o'zgartirmasdan
       qo'llanadi — bu TEKSHIRUV bo'lagi.
    4. Yonma-yon TAYANCH ham yuritiladi: hozirgi `config/default.yaml`
       aynan shu tekshiruv bo'lagida qanday natija beradi.

To'rtinchi qadam eng muhimi. Tanlangan sozlama tayanchdan yomon
chiqsa — qidiruv foyda emas, zarar keltirgan degani.

ISINISH. Har bo'lak o'zidan oldingi tarixni isinish sifatida oladi
(`core/backtest/warmup.py`), lekin uni natijaga QO'SHMAYDI. Ya'ni
ikkinchi bo'lak birinchisining shamlarini ko'radi — bu jonli
tizimdagi holatning aynan o'zi — lekin savdolari alohida sanaladi.

NIMA O'ZGARMAYDI. Ball mantig'i, chegaralar, strategiya kodi va yo'l
xarajati (komissiya + slippage) — hammasi joyida. Skript
`config/default.yaml` ga hech narsa yozmaydi.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import itertools
from dataclasses import dataclass

from core.backtest import Backtester, BacktestResult, Dataset
from core.config import AppConfig
from scripts.sinov_umumiy import (
    Bolak,
    Olchov,
    bolaklar,
    csv_saqla,
    jadval,
    kesim,
    malumot_tayyorla,
    matn_saqla,
    olchov_qur,
    umumiy_argumentlar,
)


@dataclass(frozen=True, slots=True)
class Nomzod:
    """Qidiriladigan sozlama — uchta MAVJUD parametr.

    Uchalasi ham `config/default.yaml` da bor va uchalasi ham oldingi
    o'lchovlarda natijaga ta'sir qilgani ko'ringan. Yangi parametr
    o'ylab topilmaydi: walk-forward yangi g'oya sinash uchun emas,
    tanlovning barqarorligini tekshirish uchun.
    """

    tp1_min_risk_reward: float
    min_risk_reward: float
    entry_max_range_pct: float

    def __str__(self) -> str:
        return (
            f"TP1 poli {self.tp1_min_risk_reward:g} | "
            f"nishon 1:{self.min_risk_reward:g} | "
            f"diapazon {self.entry_max_range_pct:g}%"
        )


#: Kichik to'r — 12 nomzod. Standart, chunki har bir nomzod to'liq
#: backtest degani va vaqt bo'laklar soniga ko'payadi.
TOR_KICHIK = {
    "tp1_min_risk_reward": (1.5, 2.0, 3.0),
    "min_risk_reward": (1.5, 3.0),
    "entry_max_range_pct": (45.0, 55.0),
}

#: To'liq to'r — 36 nomzod.
TOR_TOLIQ = {
    "tp1_min_risk_reward": (1.5, 2.0, 2.5, 3.0),
    "min_risk_reward": (1.5, 2.0, 3.0),
    "entry_max_range_pct": (45.0, 55.0, 65.0),
}


def _tor(nomi: str) -> list[Nomzod]:
    manba = TOR_TOLIQ if nomi == "toliq" else TOR_KICHIK
    kalitlar = list(manba)
    return [
        Nomzod(**dict(zip(kalitlar, qiymatlar, strict=True)))
        for qiymatlar in itertools.product(*(manba[k] for k in kalitlar))
    ]


def _qolla(config: AppConfig, nomzod: Nomzod) -> AppConfig:
    """Nomzodni sozlamaga qo'llaydi — faqat uchta maydon o'zgaradi."""
    qoidalar = dataclasses.replace(
        config.trade_rules, tp1_min_risk_reward=nomzod.tp1_min_risk_reward
    )
    classic = dataclasses.replace(
        config.strategies.classic_ta, min_risk_reward=nomzod.min_risk_reward
    )
    sr = dataclasses.replace(
        config.analysis.support_resistance,
        entry_max_range_pct=nomzod.entry_max_range_pct,
    )
    return dataclasses.replace(
        config,
        trade_rules=qoidalar,
        strategies=dataclasses.replace(config.strategies, classic_ta=classic),
        analysis=dataclasses.replace(config.analysis, support_resistance=sr),
    )


def _joriy_nomzod(config: AppConfig) -> Nomzod:
    """Hozirgi `config/default.yaml` dagi qiymatlar."""
    return Nomzod(
        tp1_min_risk_reward=config.trade_rules.tp1_min_risk_reward,
        min_risk_reward=config.strategies.classic_ta.min_risk_reward,
        entry_max_range_pct=config.analysis.support_resistance.entry_max_range_pct,
    )


def _yugur(
    config: AppConfig,
    dataset: Dataset,
    bolak: Bolak,
    yorliq: str,
    max_steps: int | None,
) -> BacktestResult:
    """Bitta bo'lakda backtest — kesim ichida isinish ham bor."""
    qism = kesim(dataset, bolak.kesim_boshi, bolak.tahlil_oxiri)
    return Backtester(config, label=yorliq).run(qism, max_steps=max_steps)


#: Nomzod g'olib deb tanlanishi uchun kamida shuncha savdo yopilishi kerak.
#: "Savdo qilmagan" sozlama PF bo'yicha g'olib ko'rinishi mumkin, lekin u
#: hech narsani o'lchamaydi.
ENG_KAM_SAVDO = 10


def _eng_yaxshi(
    natijalar: list[tuple[Nomzod, BacktestResult]],
) -> tuple[Nomzod, BacktestResult]:
    """PF bo'yicha eng yaxshi nomzod."""
    yaroqli = [
        (nomzod, natija)
        for nomzod, natija in natijalar
        if natija.profit_factor is not None and natija.closed >= ENG_KAM_SAVDO
    ]
    if not yaroqli:
        return natijalar[0]
    return max(yaroqli, key=lambda x: x[1].profit_factor)


#: Xulosa "tasodif emas" deyishi uchun bo'lakda kamida shuncha savdo kerak.
ISHONCHLI_SAVDO = 30


def _solishtirib_bolmaydi(tanlangan: Olchov, tayanch: Olchov) -> str | None:
    """Ikki natijani PF bo'yicha solishtirib bo'ladimi — bo'lmasa, nega.

    PF `None` bo'lishining ikki sababi bor va ular bir xil emas:
    umuman savdo yopilmagan, yoki zarar bo'lmagan (nolga bo'lish).
    Ikkalasini "savdo yo'q" deb yozish xato hisobot bo'lardi.
    """
    for nom, olchov in (("tanlangan", tanlangan), ("tayanch", tayanch)):
        if olchov.signal == 0:
            return f"{nom} sozlamada yopilgan savdo yo'q — solishtirib bo'lmaydi."
        if olchov.profit_factor is None:
            return (
                f"{nom} sozlamada zarar keltirgan savdo yo'q "
                f"({olchov.signal} savdo, hammasi foydali) — PF hisoblanmaydi."
            )
    return None


def _xulosa(
    juftlar: list[tuple[Bolak, Nomzod, Olchov, Olchov]],
) -> str:
    """Tanlov keyingi bo'lakda saqlanib qoldimi."""
    satrlar: list[str] = []
    ustunlik: list[float] = []

    for bolak, nomzod, tanlangan, tayanch in juftlar:
        sabab = _solishtirib_bolmaydi(tanlangan, tayanch)
        if sabab is not None:
            satrlar.append(f"{bolak.nomer}-bo'lak ({bolak.oraliq}): {sabab}")
            continue
        farq = tanlangan.profit_factor - tayanch.profit_factor
        ustunlik.append(farq)
        hukm = "TANLOV YAXSHIROQ" if farq > 0 else "TANLOV YOMONROQ"
        ozgina = (
            "  [DIQQAT: savdo kam, tasodif bo'lishi mumkin]"
            if min(tanlangan.signal, tayanch.signal) < ISHONCHLI_SAVDO
            else ""
        )
        satrlar.append(
            f"{bolak.nomer}-bo'lak ({bolak.oraliq}): tanlangan sozlama "
            f"[{nomzod}] PF {tanlangan.profit_factor:.2f} ({tanlangan.signal} savdo), "
            f"tayanch PF {tayanch.profit_factor:.2f} ({tayanch.signal} savdo) "
            f"-> {hukm} ({farq:+.2f}){ozgina}"
        )

    satrlar.append("")
    if not ustunlik:
        satrlar.append("Solishtirish uchun yetarli savdo yo'q.")
    elif all(f <= 0 for f in ustunlik):
        satrlar.append(
            "XULOSA: oldingi davrda tanlangan sozlama keyingi davrda tayanchdan "
            "YAXSHI CHIQMADI. Ya'ni parametr qidiruvi o'sha davrga moslashib "
            "qolgan — bu sozlamalarni backtest natijasiga qarab tanlash "
            "ishonchsiz ekanini ko'rsatadi."
        )
    elif all(f > 0 for f in ustunlik):
        satrlar.append(
            "XULOSA: tanlangan sozlama HAR BIR keyingi davrda tayanchdan yaxshi "
            "chiqdi. Bu qidiruv natijasi barqaror ekanini ko'rsatadi — lekin "
            "uchinchi, butunlay boshqa oynada takrorlanishi shart."
        )
    else:
        satrlar.append(
            "XULOSA: natija BARQAROR EMAS — ba'zi bo'lakda tanlov yaxshi, "
            "ba'zisida yomon chiqdi. Bu tasodifdan farq qilmaydi."
        )
    return "\n".join(satrlar)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="HALOL CRYPTO SAVDO — walk-forward (out-of-sample) test"
    )
    umumiy_argumentlar(parser)
    parser.add_argument(
        "--bolaklar", type=int, default=3, help="tarix necha bo'lakka bo'linsin"
    )
    parser.add_argument(
        "--grid",
        default="kichik",
        choices=("kichik", "toliq"),
        help="parametr to'ri: kichik (12 nomzod) yoki toliq (36)",
    )
    argumentlar = parser.parse_args()

    config, dataset, coinlar, oxiri = await malumot_tayyorla(argumentlar)
    qismlar = bolaklar(config, dataset, argumentlar.bolaklar)
    tor = _tor(argumentlar.grid)
    tayanch_nomzod = _joriy_nomzod(config)

    print(
        f"\nWalk-forward: {len(qismlar)} bo'lak, {len(tor)} nomzod | "
        f"{', '.join(coinlar)} | {argumentlar.days} kun"
        + (f" | {oxiri.date()} gacha" if oxiri else "")
    )
    for bolak in qismlar:
        print(f"  {bolak.nomer}-bo'lak: {bolak.oraliq}")
    print()

    olchovlar: list[Olchov] = []
    juftlar: list[tuple[Bolak, Nomzod, Olchov, Olchov]] = []

    for indeks in range(len(qismlar) - 1):
        organish = qismlar[indeks]
        tekshiruv = qismlar[indeks + 1]

        print(f"  [{organish.nomer}-bo'lak] o'rgatish — {len(tor)} nomzod sinalmoqda")
        qidiruv: list[tuple[Nomzod, BacktestResult]] = []
        for nomzod in tor:
            qidiruv.append(
                (
                    nomzod,
                    _yugur(
                        _qolla(config, nomzod),
                        dataset,
                        organish,
                        str(nomzod),
                        argumentlar.max_steps,
                    ),
                )
            )

        # G'olibning o'rgatish natijasi QAYTA yugurtirilmaydi — u
        # qidiruvda allaqachon hisoblangan.
        tanlangan, organish_natija = _eng_yaxshi(qidiruv)
        pf_matni = (
            f"{organish_natija.profit_factor:.2f}"
            if organish_natija.profit_factor is not None
            else "hisoblanmadi"
        )
        print(f"     tanlandi: {tanlangan}  (o'rgatish PF {pf_matni})")

        olchovlar.append(
            olchov_qur(
                f"{organish.nomer}-bo'lak — O'RGATISH",
                f"{organish.oraliq} | {tanlangan}",
                organish_natija,
            )
        )

        print(f"  [{tekshiruv.nomer}-bo'lak] tekshiruv — tanlov qo'llanmoqda")
        tekshiruv_natija = _yugur(
            _qolla(config, tanlangan),
            dataset,
            tekshiruv,
            "tekshiruv",
            argumentlar.max_steps,
        )
        tanlangan_olchov = olchov_qur(
            f"{tekshiruv.nomer}-bo'lak — TEKSHIRUV",
            f"{tekshiruv.oraliq} | {tanlangan}",
            tekshiruv_natija,
        )
        olchovlar.append(tanlangan_olchov)

        print(f"  [{tekshiruv.nomer}-bo'lak] tayanch — hozirgi sozlama")
        tayanch_natija = _yugur(
            _qolla(config, tayanch_nomzod),
            dataset,
            tekshiruv,
            "tayanch",
            argumentlar.max_steps,
        )
        tayanch_olchov = olchov_qur(
            f"{tekshiruv.nomer}-bo'lak — TAYANCH",
            f"{tekshiruv.oraliq} | {tayanch_nomzod}",
            tayanch_natija,
        )
        olchovlar.append(tayanch_olchov)

        juftlar.append((tekshiruv, tanlangan, tanlangan_olchov, tayanch_olchov))

    sarlavha = (
        f"WALK-FORWARD — tanlov keyingi davrda saqlanadimi\n"
        f"Coinlar: {', '.join(coinlar)} | {argumentlar.days} kun | "
        f"{len(qismlar)} bo'lak | {len(tor)} nomzod ({argumentlar.grid} to'r)"
        + (f" | oyna {oxiri.date()} gacha" if oxiri else "")
        + "\nYo'l xarajati (komissiya + slippage) dvigatel ichida hisoblangan."
    )
    matn = "\n\n".join(
        [sarlavha, jadval(olchovlar, "bo'lak", "sana oralig'i va sozlama"),
         "XULOSA", _xulosa(juftlar)]
    )

    csv_yol = csv_saqla("walk_forward.csv", olchovlar)
    matn_yol = matn_saqla("walk_forward.txt", matn)

    print("\n" + matn)
    print(f"\nSaqlandi: {csv_yol}  va  {matn_yol}")


if __name__ == "__main__":
    asyncio.run(main())
