"""XGBoost uchun DATASET — har bir nomzod bitta qator.

NIMA UCHUN BU SKRIPT BOR (2026-09-10, loyiha egasining taklifi):

    "AI ga barcha ma'lumotlarni berasiz, u o'zi qaysi biri
    haqiqatan ishlashini topadi — bu ablatsiyani AVTOMATIK
    bajaradi."

Fikr to'g'ri. Bizning ablatsiya har bir tekshiruvni BIRMA-BIR
o'chirib ko'radi. XGBoost esa BIRIKMALARNI topadi: "A tekshiruvi
faqat B yuqori bo'lganda ishlaydi". Bunday shart hech qachon
o'lchanmagan.

--------------------------------------------------------------------
UCHTA QAT'IY QOIDA — ansiz natija YOLG'ON chiqadi
--------------------------------------------------------------------

1. KELAJAKKA QARAMASLIK. Har bir qator FAQAT o'sha paytgacha
   mavjud shamlardan quriladi. `Dataset` allaqachon shu qoidani
   majburlaydi (`core/backtest/dataset.py`).

2. NATIJA BIR XIL QOIDALAR BILAN. Savdo `ZanjirBacktest._yangila`
   bilan oldinga suriladi — backtest va jonli kuzatuvchi bilan
   AYNAN bir xil. Bu yerda o'z simulyatorimizni yozsak, u asta
   ajralib ketardi va model boshqa o'yinni o'rganardi.

3. PORTFEL CHEGARASI YO'Q. Har bir nomzod MUSTAQIL baholanadi:
   "shu nomzod ochilsa, nima bo'lardi?". Chegara qo'yilsa, javob
   "o'sha paytda kapital bo'sh edimi" degan boshqa savolga
   aylanardi — va model o'shani o'rganardi.

--------------------------------------------------------------------
ZANJIR FILTRI QO'YILMAYDI
--------------------------------------------------------------------

Qatorlar zanjir uzilgan nomzodlar uchun ham yoziladi. Zanjirning
o'z natijasi (blok kuchlari, 16 ta ichki tekshiruv) — USTUN, ya'ni
model ularni o'zi baholaydi.

Ansiz dataset atigi bir necha yuz qatordan iborat bo'lardi va
XGBoost shuncha kam namunada shovqinni yodlab olardi.

Ishlatish:
    python -m scripts.zanjir_dataset --days 1460 --symbols ... --offline
"""

from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.analysis.alternatives.alternative_chain import zanjir_yur_alternativ
from core.analysis.chain.block_chain_engine import ZanjirKirish
from core.analysis.fundamental.fundamental_block import FundamentalKirish
from core.analysis.structure.swing_detector import swinglar
from core.analysis.turlar import Holat
from core.analysis.zone_quality.order_block import ObTarifi
from core.backtest.dataset import Dataset
from core.backtest.zanjir_engine import PASTKI_OYNA, Savdo, ZanjirBacktest, _shamlar
from core.position.entry_stop_tp import darajalar_qur
from scripts.zanjir_umumiy import malumot_tayyorla, umumiy_argumentlar

#: Natija fayli — `reports/` ichida, backtest natijalari bilan yonma-yon.
CHIQISH = Path("reports/zanjir_dataset.csv")

#: Savdo shuncha shamdan keyin majburan yopiladi.
#:
#: Nima uchun kerak: nomzod oxirgi shamlarda ochilsa, uning yakuni
#: ma'lumot oxiridan keyinga tushadi. Bunday qatorning yorlig'i
#: NOMA'LUM — va uni "yutqazdi" deb yozish modelga yolg'on o'rgatardi.
#: Bunday qatorlar butunlay TASHLANADI.
ENG_KOP_SHAM = 60


@dataclass(slots=True)
class Qator:
    """Bitta nomzod — ustunlar va yorliq."""

    ustunlar: dict[str, float | str]
    yorliq: str
    natija_pct: float


def _tekshiruv_qiymati(holat: Holat) -> float:
    """HA=1, YO'Q=0, MA'LUMOT YO'Q=-1.

    Nima uchun `-1`, bo'sh emas: XGBoost bo'sh qiymatni o'zi
    boshqara oladi, lekin CSV orqali o'tganda u "0" ga aylanib
    qolishi oson. `-1` esa uchinchi holat ekani ANIQ ko'rinadi va
    model uni alohida shox sifatida ajratadi.
    """
    if holat is Holat.HA:
        return 1.0
    if holat is Holat.YOQ:
        return 0.0
    return -1.0


def _ustun_nomi(nom: str) -> str:
    """Tekshiruv nomini CSV ustuni nomiga aylantiradi.

    `:` ALOHIDA e'tiborga olinadi: alternativ yo'l g'olib chiqqanda
    blokka `alternativ:<nom>` degan yangi tekshiruv QO'SHILADI
    (`alternative_chain.py`). Ya'ni ustun nomida ikki nuqta paydo
    bo'ladi va u ba'zi jadval dasturlarida ustunni bo'lib yuboradi.
    """
    toza = nom.lower()
    for belgi in (" ", "/", ":", "-", "."):
        toza = toza.replace(belgi, "_")
    return toza


def _zanjir_ustunlari(zanjir) -> dict[str, float]:  # noqa: ANN001
    """Bloklar va 16 ta ichki tekshiruv — model uchun ustun."""
    ustunlar: dict[str, float] = {
        "zanjir_toliq": 1.0 if zanjir.toliq else 0.0,
        "zanjir_ishonch": zanjir.ishonch(),
    }
    for i, blok in enumerate(zanjir.bloklar, start=1):
        ustunlar[f"blok{i}_kuch"] = float(blok.kuch)
        ustunlar[f"blok{i}_maxraj"] = float(blok.maxraj)
        ustunlar[f"blok{i}_otdi"] = 1.0 if blok.otdi else 0.0
        ustunlar[f"blok{i}_olchanmadi"] = 1.0 if blok.olchanmadi else 0.0
        for tekshiruv in blok.tekshiruvlar:
            nom = _ustun_nomi(tekshiruv.nom)
            ustunlar[f"t_{nom}"] = _tekshiruv_qiymati(tekshiruv.holat)
    return ustunlar


def _daraja_ustunlari(darajalar, narx: float) -> dict[str, float]:  # noqa: ANN001
    """Kirish/Stop/TP — FOIZDA, mutlaq narxda emas.

    Sabab: BTC 60000, ADA 0.5. Mutlaq narx model uchun coin nomini
    bildiruvchi yashirin belgi bo'lib qolardi va model "BTC bo'lsa
    shunday" deb o'rganardi — bu strategiya emas.
    """
    entry = darajalar.entry
    tplar = darajalar.tplar
    return {
        "stop_pct": (entry - darajalar.stop) / entry * 100,
        "tp1_pct": (tplar[0] - entry) / entry * 100,
        "tp_soni": float(len(tplar)),
        "nisbat": (tplar[0] - entry) / (entry - darajalar.stop),
        # Narx entry'dan qancha YUQORIDA — limit bajarilish ehtimoli
        # shundan ko'rinadi. Bu maydon hozirgi qoidalarda YO'Q va
        # aynan shuning uchun qiziq.
        "narx_entry_farq_pct": (narx - entry) / entry * 100,
    }


def _bozor_ustunlari(shamlar, btc) -> dict[str, float]:  # noqa: ANN001
    """Coin va BTC ning yaqin o'tmishi — kontekst.

    Zanjir bu raqamlarni ICHIDA ishlatadi, lekin tashqariga faqat
    "ha/yo'q" beradi. Model uchun xom o'lchov ham foydali bo'lishi
    mumkin — buni o'lchash kerak, taxmin qilmaslik.
    """

    def ozgarish(qator, n: int) -> float:  # noqa: ANN001
        if len(qator) <= n:
            return 0.0
        eski = qator[-n - 1].close
        return (qator[-1].close - eski) / eski * 100 if eski else 0.0

    oxirgi = shamlar[-20:]
    yuqori = max(s.high for s in oxirgi)
    past = min(s.low for s in oxirgi)
    orta = shamlar[-1].close
    return {
        "coin_ozg_5": ozgarish(shamlar, 5),
        "coin_ozg_20": ozgarish(shamlar, 20),
        "btc_ozg_5": ozgarish(btc, 5),
        "btc_ozg_20": ozgarish(btc, 20),
        # 20 shamlik diapazonda narx qayerda: 0 — tubida, 1 — cho'qqisida
        "diapazon_orni": (orta - past) / (yuqori - past) if yuqori > past else 0.5,
        "diapazon_kengligi_pct": (yuqori - past) / orta * 100 if orta else 0.0,
    }


def _yigish(config, dataset: Dataset, symbols: list[str], max_qadam: int | None):  # noqa: ANN001, ANN202
    """Har bir coin × har bir qadam uchun bitta qator."""
    # Motorning O'ZI ishlatiladi — chiqish qoidalari bir xil bo'lsin.
    motor = ZanjirBacktest(config, "dataset", alternativ=True)
    z = config.zanjir

    vaqtlar = dataset.timeline(z.timeframelar.asosiy)
    if max_qadam is not None:
        vaqtlar = vaqtlar[-max_qadam:]

    qatorlar: list[Qator] = []
    tashlandi = 0

    for indeks, hozir in enumerate(vaqtlar):
        btc = _shamlar(dataset, "BTC", z.timeframelar.asosiy, hozir)
        if len(btc) < 30:  # noqa: PLR2004
            continue
        # Yakuni ma'lumot oxiridan keyinga tushadigan nomzodlar
        # TASHLANADI — yorlig'i noma'lum.
        if indeks + ENG_KOP_SHAM >= len(vaqtlar):
            continue

        for symbol in symbols:
            shamlar = _shamlar(dataset, symbol, z.timeframelar.asosiy, hozir)
            if len(shamlar) < 30:  # noqa: PLR2004
                continue
            narx = shamlar[-1].close

            natijasi = zanjir_yur_alternativ(
                ZanjirKirish(
                    symbol=symbol,
                    shamlar=shamlar,
                    pastki_shamlar=_shamlar(
                        dataset, symbol, z.timeframelar.tasdiq, hozir, PASTKI_OYNA
                    ),
                    btc_shamlar=btc,
                    fundamental=FundamentalKirish(),
                    etalon=symbol.upper() == "BTC",
                    ob_tarifi=ObTarifi(z.bloklar.ob_tarifi),
                    unlock_yaqin_kun=z.bloklar.unlock_yaqin_kun,
                    unlock_katta_pct=z.bloklar.unlock_katta_pct,
                )
            )
            zona = natijasi.zona_natija.zona if natijasi.zona_natija else None
            if zona is None:
                continue

            # Darajalar QOIDASIZ quriladi: rad etish sabablari ham
            # ustun bo'lib model uchun ma'lumot bo'lishi mumkin.
            # Faqat qurib bo'lmaydigan holat tashlanadi.
            darajalar = darajalar_qur(
                zona,
                swinglar(shamlar),
                narx,
                eng_kam_stop_pct=0.0,
                eng_kop_stop_pct=100.0,
                eng_kam_nisbat=0.0,
                eng_kop_tp=z.darajalar.tp_eng_kop,
                eng_kam_oraliq_pct=z.darajalar.tp_eng_kam_oraliq_pct,
                likvidlik_bufer_pct=z.darajalar.stop_likvidlik_bufer_pct,
                nishon_narxdan_yuqori=False,
            )
            if not darajalar.yaroqli:
                continue

            yorliq, natija_pct = _yakunini_top(
                motor, dataset, symbol, darajalar, hozir, vaqtlar, indeks, z
            )
            if yorliq == "nomalum":
                tashlandi += 1
                continue

            ustunlar: dict[str, float | str] = {"symbol": symbol, "vaqt": hozir.isoformat()}
            ustunlar.update(_zanjir_ustunlari(natijasi.zanjir))
            ustunlar.update(_daraja_ustunlari(darajalar, narx))
            ustunlar.update(_bozor_ustunlari(shamlar, btc))
            qatorlar.append(Qator(ustunlar, yorliq, natija_pct))

    return qatorlar, tashlandi


def _yakunini_top(  # noqa: ANN202, PLR0913
    motor: ZanjirBacktest,
    dataset: Dataset,
    symbol: str,
    darajalar,  # noqa: ANN001
    signal_vaqti: datetime,
    vaqtlar: list[datetime],
    indeks: int,
    z,  # noqa: ANN001
):
    """Nomzodni oldinga suradi va yakunini qaytaradi.

    Motorning `_yangila` metodi ISHLATILADI — u backtest va jonli
    kuzatuvchi bilan bir xil qoidalarni yuritadi. O'z nusxamizni
    yozsak, u asta ajralib ketardi.
    """
    savdo = Savdo(
        symbol=symbol,
        kirish_vaqti=signal_vaqti,
        signal_vaqti=signal_vaqti,
        entry=darajalar.entry,
        stop=darajalar.stop,
        tplar=darajalar.tplar,
    )
    for keyingi in vaqtlar[indeks + 1 : indeks + 1 + ENG_KOP_SHAM]:
        shamlar = _shamlar(dataset, symbol, z.timeframelar.asosiy, keyingi)
        if not shamlar:
            continue
        holat = motor._yangila(savdo, shamlar[-1], keyingi)  # noqa: SLF001
        if holat == "yopildi":
            return savdo.sabab or "yopildi", savdo.natija_pct
        if holat == "bekor":
            return "bekor", 0.0
    return "nomalum", 0.0


#: Ustuni yo'q qatorga qo'yiladigan qiymat — "o'lchanmadi".
#: `_tekshiruv_qiymati` bilan bir xil ma'no.
YOQ_QIYMAT = -1.0

#: Har doim birinchi turadigan ustunlar — model uchun emas, ODAM uchun.
BOSH_USTUNLAR = ("symbol", "vaqt")


def _csv_yoz(qatorlar: list[Qator], yol: Path) -> list[str]:
    """Jadvalni yozadi va ustun nomlarini qaytaradi.

    HAR BIR QATORDA USTUNLAR TO'PLAMI HAR XIL BO'LISHI MUMKIN —
    va bu birinchi yugurishda butun ishni yiqitdi.

    Sabab: alternativ yo'l g'olib chiqqanda blokka `alternativ:<nom>`
    degan YANGI tekshiruv qo'shiladi (`alternative_chain.py`, 184-qator).
    Ya'ni ba'zi qatorlarda qo'shimcha ustun bo'ladi, ba'zilarida yo'q.

    `csv.DictWriter` birinchi qatorning kalitlarini olib, keyingi
    qatorda ortiqcha kalit ko'rsa `ValueError` bilan yiqiladi.

    Yechim: BARCHA qatorlarning ustunlari birlashtiriladi, yetishmagani
    esa `-1` bilan to'ldiriladi — ya'ni "bu tekshiruv umuman
    ishlamadi", `MALUMOT_YOQ` bilan bir xil ma'no.
    """
    hammasi: set[str] = set()
    for q in qatorlar:
        hammasi.update(q.ustunlar)
    # Tartib QAT'IY: ikki yugurish bir xil ustun tartibini bersin,
    # aks holda ikkita CSV ni solishtirib bo'lmasdi.
    qolgan = sorted(hammasi - set(BOSH_USTUNLAR))
    ustun_nomlari = [*BOSH_USTUNLAR, *qolgan, "yorliq", "natija_pct", "yutdi"]

    with yol.open("w", newline="", encoding="utf-8") as f:
        yozuvchi = csv.DictWriter(f, fieldnames=ustun_nomlari)
        yozuvchi.writeheader()
        for q in qatorlar:
            satr: dict[str, float | str] = {
                nom: q.ustunlar.get(nom, YOQ_QIYMAT) for nom in qolgan
            }
            for nom in BOSH_USTUNLAR:
                satr[nom] = q.ustunlar.get(nom, "")
            satr["yorliq"] = q.yorliq
            satr["natija_pct"] = round(q.natija_pct, 4)
            satr["yutdi"] = 1 if q.natija_pct > 0 else 0
            yozuvchi.writerow(satr)
    return ustun_nomlari


async def main() -> None:
    argumentlar = umumiy_argumentlar(__doc__ or "").parse_args()
    config, dataset, symbols = await malumot_tayyorla(argumentlar)

    print("  dataset yig'ilmoqda ...")
    qatorlar, tashlandi = _yigish(config, dataset, symbols, argumentlar.max_steps)

    if not qatorlar:
        print("🔴 Bitta ham qator yig'ilmadi.")
        return

    CHIQISH.parent.mkdir(parents=True, exist_ok=True)
    ustun_nomlari = _csv_yoz(qatorlar, CHIQISH)

    yakunlar: dict[str, int] = {}
    for q in qatorlar:
        yakunlar[q.yorliq] = yakunlar.get(q.yorliq, 0) + 1

    print()
    print(f"Qatorlar: {len(qatorlar)} | ustunlar: {len(ustun_nomlari)}")
    print(f"Yorlig'i noma'lum bo'lgani tashlandi: {tashlandi}")
    print()
    print("Yakunlar:")
    for nom, soni in sorted(yakunlar.items(), key=lambda x: -x[1]):
        ulush = soni / len(qatorlar) * 100
        print(f"   {soni:6d}  ({ulush:5.1f}%)  {nom}")

    savdolar = [q for q in qatorlar if q.yorliq != "bekor"]
    if savdolar:
        yutgan = sum(1 for q in savdolar if q.natija_pct > 0)
        print()
        print(f"Ochilgan savdolar: {len(savdolar)}, yutgan: {yutgan / len(savdolar) * 100:.1f}%")
    print()
    print(f"Saqlandi: {CHIQISH}")


if __name__ == "__main__":
    asyncio.run(main())
