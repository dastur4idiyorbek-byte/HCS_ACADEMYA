"""XGBoost MODELI — o'rgatish, imtihon, ustunlar muhimligi.

--------------------------------------------------------------------
NIMA QILADI
--------------------------------------------------------------------

`scripts/zanjir_dataset.py` yig'gan jadvalni oladi va uchta savolga
javob beradi:

    1. Model tayanchdan (hozirgi qoidalardan) yaxshimi?
    2. Qaysi ustunlar haqiqatan ishlatildi?
    3. Natija VAQT bo'yicha saqlanadimi?

--------------------------------------------------------------------
WALK-FORWARD — TASODIFIY BO'LISH EMAS
--------------------------------------------------------------------

Vaqt qatorida `train/test` ni tasodifiy bo'lish — eng keng
tarqalgan va eng qimmat xato. Model kelasi haftani o'tgan haftadan
o'rganib qo'yadi va imtihonda "a'lo" chiqadi.

Bu yerda bo'lish DOIM vaqt bo'yicha:

    1-oyna:  [o'rgatish........][imtihon]
    2-oyna:  [o'rgatish.............][imtihon]
    3-oyna:  [o'rgatish..................][imtihon]

Model HAR BIR oynada tayanchdan yaxshi bo'lishi kerak — o'rtacha
hisobda emas. Bitta oynada yaxshi, ikkitasida yomon bo'lsa, bu
tasodif.

--------------------------------------------------------------------
YORLIQ VA BAHOLASH
--------------------------------------------------------------------

Model BARCHA qatorlarda o'rgatiladi — `bekor` (limit bajarilmagan)
qatorlar ham. Sabab: ular ham qaror natijasi. Jonli tizimda biz
signalni OLDINDAN beramiz va limit bajarilishini bilmaymiz.
`bekor` qator uchun natija 0% — zarar ham, foyda ham yo'q.

Baholash SOF PUL bilan: model "ol" degan qatorlarning haqiqiy
`natija_pct` yig'indisi. Chiroyli "aniqlik foizi" ATAYLAB asosiy
o'lchov emas — 66% qator `bekor` bo'lgani uchun "hech narsa
qilma" degan model ham 66% aniqlik olardi.

Ishlatish:
    python -m scripts.zanjir_model
    python -m scripts.zanjir_model --oynalar 4 --ulush 0.15
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import xgboost as xgb

MANBA = Path("reports/zanjir_dataset.csv")
MUHIMLIK_YOLI = Path("reports/zanjir_muhimlik.csv")

#: Ustun sifatida ISHLATILMAYDIGAN maydonlar.
#:
#: `symbol` ATAYLAB tashlanadi: model "BTC bo'lsa yaxshi" deb
#: o'rganib qolardi va bu strategiya emas, o'tmishga moslashish
#: bo'lardi.
TASHLANADI = ("symbol", "vaqt", "yorliq", "natija_pct", "yutdi")

#: Model shu ehtimoldan yuqori bergan qatorni "ol" deb hisoblaymiz.
#: Bir necha qiymat sinaladi — qaysi biri eng ko'p pul beradi.
CHEGARALAR = (0.35, 0.40, 0.45, 0.50, 0.55, 0.60)


def _argumentlar() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manba", default=str(MANBA))
    p.add_argument("--oynalar", type=int, default=4, help="walk-forward oynalari")
    p.add_argument("--ulush", type=float, default=0.2, help="imtihon ulushi")
    return p.parse_args()


def _tayanch_belgisi(jadval: pd.DataFrame) -> pd.Series:
    """HOZIRGI QOIDALAR shu qatorni signal qilarmidi.

    Dataset barcha nomzodlarni oladi, jonli tizim esa faqat zanjir
    to'liq va darajalar chegaradan o'tganlarini. Solishtirish HALOL
    bo'lishi uchun tayanch aynan shu shartlar bilan quriladi.

    Chegaralar `config/default.yaml` dagi qiymatlar bilan bir xil
    bo'lishi kerak; ular o'zgarsa bu yer ham o'zgaradi.
    """
    return (
        (jadval["zanjir_toliq"] == 1)
        & (jadval["stop_pct"] >= 1.5)  # noqa: PLR2004
        & (jadval["stop_pct"] <= 15.0)  # noqa: PLR2004
        & (jadval["nisbat"] >= 1.2)  # noqa: PLR2004
        & (jadval["narx_entry_farq_pct"] >= -0.3)  # noqa: PLR2004
        & (jadval["tp1_pct"] > jadval["narx_entry_farq_pct"])
    )


def _xulosa(natijalar: pd.Series, nom: str) -> dict[str, float]:
    """Tanlangan qatorlar bo'yicha pul o'lchovlari."""
    savdolar = natijalar[natijalar != 0]
    yutgan = savdolar[savdolar > 0].sum()
    yutqazgan = -savdolar[savdolar < 0].sum()
    return {
        "nom": nom,
        "signal": int(len(natijalar)),
        "savdo": int(len(savdolar)),
        "foydali_pct": float((savdolar > 0).mean() * 100) if len(savdolar) else 0.0,
        "pf": float(yutgan / yutqazgan) if yutqazgan > 0 else float("inf"),
        "jami_pct": float(savdolar.sum()),
        "ortacha_pct": float(savdolar.mean()) if len(savdolar) else 0.0,
    }


def _jadval_chop(qatorlar: list[dict]) -> None:
    if not qatorlar:
        print("   (bo'sh)")
        return
    print(
        f"{'konfiguratsiya':<30}{'signal':>8}{'savdo':>8}"
        f"{'foydali':>9}{'PF':>7}{'jami%':>9}{'o‘rt.%':>8}"
    )
    print("-" * 79)
    for q in qatorlar:
        pf = "∞" if q["pf"] == float("inf") else f"{q['pf']:.2f}"
        print(
            f"{q['nom']:<30}{q['signal']:>8}{q['savdo']:>8}"
            f"{q['foydali_pct']:>8.1f}%{pf:>7}{q['jami_pct']:>9.1f}{q['ortacha_pct']:>8.2f}"
        )


def main() -> None:
    a = _argumentlar()
    jadval = pd.read_csv(a.manba)
    jadval = jadval.sort_values("vaqt").reset_index(drop=True)

    ustunlar = [u for u in jadval.columns if u not in TASHLANADI]
    X = jadval[ustunlar].astype(float)
    y = jadval["yutdi"].astype(int)
    natija = jadval["natija_pct"].astype(float)
    tayanch = _tayanch_belgisi(jadval)

    print(f"Qatorlar: {len(jadval)} | ustunlar: {len(ustunlar)}")
    print(f"Yutgan qatorlar: {y.mean() * 100:.1f}%")
    print()

    imtihon_hajmi = int(len(jadval) * a.ulush)
    if imtihon_hajmi < 200:  # noqa: PLR2004
        print("🔴 Imtihon oynasi juda kichik — natija ishonchsiz.")
        return

    barcha_muhimlik: list[pd.Series] = []
    oyna_xulosalari: list[list[dict]] = []

    for oyna in range(a.oynalar):
        # Oyna oldinga suriladi: o'rgatish qismi o'sib boradi,
        # imtihon esa DOIM undan KEYIN keladi.
        oxir = len(jadval) - (a.oynalar - 1 - oyna) * imtihon_hajmi
        boshi = oxir - imtihon_hajmi
        if boshi < imtihon_hajmi:
            continue

        Xo, yo_ = X.iloc[:boshi], y.iloc[:boshi]
        Xi = X.iloc[boshi:oxir]

        # ASOSIY API (`xgb.train`), `XGBClassifier` EMAS.
        #
        # Sabab: `XGBClassifier` — scikit-learn qobig'i va u
        # scikit-learn o'rnatilishini TALAB qiladi. Bu yana bir
        # og'ir kutubxona, bizga esa faqat o'rgatish va bashorat
        # kerak. Asosiy API ikkalasini ham beradi.
        motor = xgb.train(
            {
                "objective": "binary:logistic",
                "eval_metric": "logloss",
                "max_depth": 4,
                "eta": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                # Kuchli tartibga solish — 16 mingta qator va 50
                # ustunda model shovqinni yodlab olishi oson.
                "lambda": 5.0,
                "min_child_weight": 20,
                "nthread": 2,
            },
            xgb.DMatrix(Xo, label=yo_),
            num_boost_round=300,
        )
        ehtimol = motor.predict(xgb.DMatrix(Xi))

        imtihon_natija = natija.iloc[boshi:oxir].reset_index(drop=True)
        imtihon_tayanch = tayanch.iloc[boshi:oxir].reset_index(drop=True)

        qatorlar = [_xulosa(imtihon_natija[imtihon_tayanch], "TAYANCH (hozirgi qoidalar)")]
        for chegara in CHEGARALAR:
            tanlov = pd.Series(ehtimol >= chegara)
            if tanlov.sum() == 0:
                continue
            qatorlar.append(_xulosa(imtihon_natija[tanlov], f"model >= {chegara:.2f}"))

        print(f"--- {oyna + 1}-oyna: o'rgatish {boshi}, imtihon {imtihon_hajmi} qator")
        _jadval_chop(qatorlar)
        print()
        oyna_xulosalari.append(qatorlar)

        # `get_score` FAQAT ishlatilgan ustunlarni qaytaradi —
        # ishlatilmaganlari umuman yo'q. Ular 0 bilan to'ldiriladi,
        # aks holda "ro'yxatda yo'q" va "muhimligi nol" farqi
        # yo'qolardi va o'rtacha noto'g'ri chiqardi.
        ballar = motor.get_score(importance_type="gain")
        barcha_muhimlik.append(
            pd.Series({nom: ballar.get(nom, 0.0) for nom in ustunlar})
        )

    if not barcha_muhimlik:
        print("🔴 Bironta oyna ham qurilmadi — ma'lumot kam.")
        return

    muhimlik = pd.concat(barcha_muhimlik, axis=1).mean(axis=1).sort_values(ascending=False)
    muhimlik = muhimlik / muhimlik.sum() * 100

    MUHIMLIK_YOLI.parent.mkdir(parents=True, exist_ok=True)
    muhimlik.to_csv(MUHIMLIK_YOLI, header=["muhimlik_pct"])

    print("=" * 79)
    print("USTUNLAR MUHIMLIGI (barcha oynalar o'rtachasi)")
    print("=" * 79)
    for nom, qiymat in muhimlik.head(20).items():
        chiziq = "█" * int(qiymat / 2)
        print(f"{nom:<34}{qiymat:>6.2f}%  {chiziq}")
    print()
    ishlatilmagan = muhimlik[muhimlik < 0.5].index.tolist()  # noqa: PLR2004
    if ishlatilmagan:
        print(f"Deyarli ishlatilmagan ({len(ishlatilmagan)} ta):")
        print("   " + ", ".join(ishlatilmagan[:25]))
    print()

    _yakuniy_xulosa(oyna_xulosalari)
    print(f"Muhimlik saqlandi: {MUHIMLIK_YOLI}")


def _yakuniy_xulosa(oyna_xulosalari: list[list[dict]]) -> None:
    """TO'XTASH QOIDASI — model har bir oynada yaxshimi."""
    print("=" * 79)
    print("XULOSA")
    print("=" * 79)

    galabalar = 0
    for i, qatorlar in enumerate(oyna_xulosalari, start=1):
        tayanch = qatorlar[0]
        modellar = [q for q in qatorlar[1:] if q["savdo"] >= 20]  # noqa: PLR2004
        if not modellar:
            print(f"{i}-oyna: model yetarli savdo bermadi")
            continue
        eng = max(modellar, key=lambda q: q["jami_pct"])
        belgi = "🟢" if eng["jami_pct"] > tayanch["jami_pct"] else "🔴"
        galabalar += 1 if eng["jami_pct"] > tayanch["jami_pct"] else 0
        print(
            f"{i}-oyna: {belgi} tayanch {tayanch['jami_pct']:+.1f}% "
            f"({tayanch['savdo']} savdo) | eng yaxshi model «{eng['nom']}» "
            f"{eng['jami_pct']:+.1f}% ({eng['savdo']} savdo)"
        )

    jami = len(oyna_xulosalari)
    print()
    if galabalar == jami and jami >= 3:  # noqa: PLR2004
        print(f"🟢 Model {jami}/{jami} oynada tayanchdan yaxshi.")
        print("   KEYINGI QADAM: chegarani tanlab, jonli sinovga tayyorlash.")
    elif galabalar == 0:
        print(f"⚫ Model 0/{jami} oynada tayanchdan yaxshi emas.")
        print("   Ustunlarimizda kelajak haqida ma'lumot YO'Q.")
        print("   YANGI MA'LUMOT MANBAI kerak — fundamental, on-chain, yangilik.")
    else:
        print(f"🟡 Model {galabalar}/{jami} oynada yaxshi — BARQAROR EMAS.")
        print("   Bu tasodif bo'lishi mumkin. Xulosa chiqarilmaydi.")


if __name__ == "__main__":
    main()
