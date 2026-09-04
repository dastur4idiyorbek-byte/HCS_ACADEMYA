"""1000 DOLLAR bo'lganda nima bo'lardi — hisob simulyatsiyasi.

Backtest "PF 3.50" deydi. Bu — savdolarning o'zaro nisbati, LEKIN
u hisobda nima bo'lishini AYTMAYDI. Sabab: har bir savdoda qancha
pul ishlatilishi Stop masofasiga va kunlik xavf byudjetiga
bog'liq, ya'ni bir xil PF butunlay boshqa daromad berishi mumkin.

Bu skript o'sha bo'shliqni yopadi: backtest savdolarini oladi va
ularni loyihaning O'Z pozitsiya hajmi qoidalari bilan yuritadi
(`core/position_sizing`). Ya'ni raqam TAXMIN emas — tizimning o'zi
tavsiya qiladigan hajmlardan chiqadi.

QOIDALAR (config'dan olinadi, bu yerda takrorlanmaydi):
  - kunlik xavf: 1000$ gacha 3%, 10 000$ gacha 2%, undan yuqori 1.5%
  - har signalga qolgan byudjetning 34% i (sequential_decay)
  - SPOT: leverage yo'q, pozitsiya balansdan oshmaydi
  - kapital ham taqsimlanadi, aks holda birinchi signal hammasini oladi

NIMA HISOBGA OLINMAYDI (ochiq aytiladi):
  - obuna to'lovi
  - soliq
  - foydalanuvchi signalni QO'LDA bajaradi: kechikish, o'tkazib
    yuborilgan signal, boshqa narxda kirish
  - birjadagi minimal savdo hajmi

Shuning uchun natija — YUQORI CHEGARA, va'da emas.

Ishlatish:
    python -m scripts.zanjir_hisob --days 730 --offline --balans 1000
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

from core.backtest.zanjir_engine import Savdo, ZanjirBacktest
from core.config.schema import AppConfig
from core.domain.models import SignalLevels, TakeProfit
from core.position_sizing.sizer import PositionSizer
from scripts.zanjir_umumiy import malumot_tayyorla, umumiy_argumentlar

#: Bir oyda o'rtacha shuncha kun (365.25 / 12).
OYDAGI_KUN = 30.44


@dataclass
class HisobNatijasi:
    boshlangich: float
    yakuniy: float
    kunlar: float
    bajarilgan: int
    otkazilgan: int
    eng_chuqur_pasayish_pct: float

    @property
    def oylar(self) -> float:
        return self.kunlar / OYDAGI_KUN

    @property
    def jami_pct(self) -> float:
        return (self.yakuniy / self.boshlangich - 1) * 100

    @property
    def oylik_pct(self) -> float:
        """Qo'shilib boradigan (compound) oylik o'sish."""
        if self.oylar <= 0 or self.yakuniy <= 0:
            return 0.0
        return ((self.yakuniy / self.boshlangich) ** (1 / self.oylar) - 1) * 100


def _darajalar(savdo: Savdo) -> SignalLevels | None:
    """Savdodan `SignalLevels` yasaydi. Yaroqsiz bo'lsa `None`."""
    n = len(savdo.tplar)
    if n == 1:
        ulushlar = [100.0]
    elif n == 2:  # noqa: PLR2004
        ulushlar = [50.0, 50.0]
    else:
        ulushlar = [50.0, 30.0, 20.0]
    ulushlar = ulushlar[:n]
    ulushlar[-1] += 100.0 - sum(ulushlar)
    try:
        return SignalLevels(
            entry=savdo.entry,
            stop=savdo.stop,
            takes=tuple(
                TakeProfit(price=narx, close_pct=ulush)
                for narx, ulush in zip(savdo.tplar, ulushlar, strict=True)
            ),
        )
    except ValueError:
        # Muddat bo'yicha yopilgan savdoda Stop breakeven'ga surilgan
        # bo'lishi mumkin, ya'ni Stop == Entry. Bunday holat hajm
        # hisobiga yaroqsiz va JIM tashlanmaydi — sanaladi.
        return None


def hisobni_yurit(savdolar: list[Savdo], config: AppConfig, balans: float) -> HisobNatijasi:
    """Savdolarni vaqt tartibida hisobda "yashab ko'radi"."""
    sizer = PositionSizer(config.position_sizing)
    boshlangich = balans

    hodisalar: list[tuple[datetime, int, Savdo]] = []
    for s in savdolar:
        if s.chiqish_vaqti is None:
            continue
        hodisalar.append((s.kirish_vaqti, 0, s))
        hodisalar.append((s.chiqish_vaqti, 1, s))
    # Yopilish OCHILISHDAN oldin ishlanadi (ikkinchi kalit): shu
    # kunda bo'shagan kapital o'sha kuni qayta ishlatilishi mumkin.
    hodisalar.sort(key=lambda x: (x[0], -x[1]))

    hajmlar: dict[int, float] = {}
    bajarilgan = otkazilgan = 0
    byudjet = None
    byudjet_kuni = None
    choqqi = balans
    eng_pasayish = 0.0

    if not hodisalar:
        return HisobNatijasi(boshlangich, balans, 0.0, 0, 0, 0.0)

    for vaqt, turi, savdo in hodisalar:
        if turi == 1:
            hajm = hajmlar.pop(id(savdo), None)
            if hajm is None:
                continue
            balans += hajm * savdo.natija_pct / 100
            if byudjet is not None:
                byudjet.release_capital(hajm)
            choqqi = max(choqqi, balans)
            eng_pasayish = max(eng_pasayish, (choqqi - balans) / choqqi * 100)
            continue

        kun = vaqt.date()
        if byudjet_kuni != kun:
            # Yangi kun — yangi xavf byudjeti, LEKIN band kapital
            # saqlanadi: ochiq pozitsiyalar yopilmagan.
            band = byudjet.committed_capital if byudjet is not None else 0.0
            byudjet = sizer.budget_for(balans)
            byudjet.committed_capital = band
            byudjet_kuni = kun

        daraja = _darajalar(savdo)
        if daraja is None:
            otkazilgan += 1
            continue
        tavsiya = sizer.suggest(savdo.symbol, daraja, byudjet, commit=True)
        if tavsiya.position_size_usd <= 0:
            otkazilgan += 1
            continue
        hajmlar[id(savdo)] = tavsiya.position_size_usd
        bajarilgan += 1

    kunlar = (hodisalar[-1][0] - hodisalar[0][0]).total_seconds() / 86400
    return HisobNatijasi(
        boshlangich=boshlangich,
        yakuniy=balans,
        kunlar=kunlar,
        bajarilgan=bajarilgan,
        otkazilgan=otkazilgan,
        eng_chuqur_pasayish_pct=eng_pasayish,
    )


async def main() -> None:
    parser = umumiy_argumentlar(__doc__ or "")
    parser.add_argument("--balans", type=float, default=1000.0)
    argumentlar = parser.parse_args()

    config, dataset, symbols = await malumot_tayyorla(argumentlar)

    print("  ishlamoqda: sig'im bilan (jonli tizimga eng yaqin holat) ...")
    natija = ZanjirBacktest(config, "hisob", sigim=True).yur(
        dataset, symbols, argumentlar.max_steps
    )

    hisob = hisobni_yurit(natija.savdolar, config, argumentlar.balans)

    print()
    print(f"Coinlar: {', '.join(symbols)} | {argumentlar.days} kun")
    print()
    print(f"Boshlang'ich balans:      ${hisob.boshlangich:,.0f}")
    print(f"Yakuniy balans:           ${hisob.yakuniy:,.0f}")
    print(f"Davr:                     {hisob.kunlar:.0f} kun ({hisob.oylar:.1f} oy)")
    print(f"Bajarilgan savdo:         {hisob.bajarilgan}")
    print(f"O'tkazib yuborilgan:      {hisob.otkazilgan}  (byudjet/kapital yetmadi)")
    print(f"Oyiga o'rtacha savdo:     {hisob.bajarilgan / max(hisob.oylar, 1e-9):.1f}")
    print()
    print(f"JAMI:                     {hisob.jami_pct:+.1f}%")
    print(f"OYLIK (qo'shilib borgan): {hisob.oylik_pct:+.2f}%")
    print(f"Eng chuqur pasayish:      {hisob.eng_chuqur_pasayish_pct:.1f}%")
    print()
    _ogohlantirish(hisob)


def _ogohlantirish(hisob: HisobNatijasi) -> None:
    print("⚠️ BU RAQAM VA'DA EMAS. Hisobga OLINMAGAN:")
    print("   • obuna to'lovi va soliq")
    print("   • signalni qo'lda bajarish: kechikish, o'tkazib yuborish,")
    print("     boshqa narxda kirish")
    print("   • birjadagi minimal savdo hajmi")
    print("   • kelajak o'tmishga o'xshamasligi")
    print()
    if hisob.bajarilgan < 100:  # noqa: PLR2004
        print(f"⚠️ Atigi {hisob.bajarilgan} savdo — bu raqam TASODIFGA yaqin.")
    if hisob.eng_chuqur_pasayish_pct >= 30:  # noqa: PLR2004
        print(
            f"🔴 Yo'lda balans {hisob.eng_chuqur_pasayish_pct:.0f}% ga tushgan. "
            "Ko'p odam shu yerda to'xtaydi —"
        )
        print("   ya'ni yakuniy raqamgacha yetib bormaydi.")


if __name__ == "__main__":
    asyncio.run(main())
