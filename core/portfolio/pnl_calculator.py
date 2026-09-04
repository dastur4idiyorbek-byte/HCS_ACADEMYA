"""3-qism: Realized va Unrealized PNL hisoblash.

QOIDA (3-prompt, 3-qism):

    Realized    — YOPILGAN qismlarning haqiqiy foyda/zarari,
                  tanlangan davr ichida yig'ilgan
    Unrealized  — hozir OCHIQ savdolarning joriy narxdagi holati

    Ikkalasi ARALASHTIRILMAYDI — alohida ko'rsatiladi.

ENG MUHIM TALAB: "har kunlik/haftalik/oylik foiz QATTIQ FORMULA
bilan oldindan taxmin qilinmaydi, balki HAR SAFAR haqiqiy
savdolar asosida dinamik qayta hisoblanadi".

Shuning uchun bu faylda birorta ham "kutilayotgan oylik foyda"
turidagi doimiy yo'q. Hamma raqam kiruvchi yozuvlardan chiqadi.
Yozuv bo'lmasa — nol qaytadi, taxminiy raqam emas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

#: Dashboard davrlari: kalit -> necha kun (None = boshidan beri).
DAVRLAR: dict[str, int | None] = {
    "bugun": 1,
    "hafta": 7,
    "oy": 30,
    "boshidan": None,
}


@dataclass(frozen=True, slots=True)
class YopilganQism:
    """Bitta yopilgan qism — TP bosqichi yoki Stop.

    NIMA UCHUN "QISM", SIGNAL EMAS. Signal N ta TP bilan
    bosqichma-bosqich yopiladi. Har bosqich o'z narxida va o'z
    vaqtida sotiladi, ya'ni ular BOSHQA kunlarga tushishi mumkin.
    "Bugungi PNL" ni to'g'ri hisoblash uchun yozuv qism darajasida
    bo'lishi shart.
    """

    signal_id: int
    symbol: str
    yopilgan_vaqt: datetime
    #: Shu qismga ketgan pul (pozitsiyaning ulushi).
    miqdor_usd: float
    #: Foyda (musbat) yoki zarar (manfiy), dollarda.
    natija_usd: float
    sabab: str = ""


@dataclass(frozen=True, slots=True)
class OchiqPozitsiya:
    """Hozir ochiq turgan savdo — joriy narx bilan baholanadi."""

    signal_id: int
    symbol: str
    entry: float
    #: Hali sotilmagan qismning puldagi hajmi.
    ochiq_miqdor_usd: float
    joriy_narx: float

    @property
    def unrealized_usd(self) -> float:
        if self.entry <= 0:
            return 0.0
        return self.ochiq_miqdor_usd * (self.joriy_narx - self.entry) / self.entry


@dataclass(frozen=True, slots=True)
class DavrNatijasi:
    """Bitta davr uchun hisoblangan natija."""

    nom: str
    realized_usd: float
    #: Foiz — BOSHLANG'ICH balansga nisbatan.
    realized_pct: float
    savdo_soni: int


@dataclass(frozen=True, slots=True)
class PnlXulosasi:
    """Dashboard uchun to'liq manzara."""

    davrlar: tuple[DavrNatijasi, ...]
    unrealized_usd: float
    ochiq_soni: int
    balans_usd: float

    def davr(self, nom: str) -> DavrNatijasi | None:
        for d in self.davrlar:
            if d.nom == nom:
                return d
        return None


def _kesim(hozir: datetime, kun: int | None) -> datetime | None:
    if kun is None:
        return None
    if kun == 1:
        # "Bugun" — kalendar kun boshi, oxirgi 24 soat emas.
        # Foydalanuvchi "bugungi natija" deganda ertalabdan
        # beri bo'lganini tushunadi.
        return hozir.replace(hour=0, minute=0, second=0, microsecond=0)
    return hozir - timedelta(days=kun)


def realized_hisobla(
    qismlar: list[YopilganQism],
    balans_usd: float,
    hozir: datetime | None = None,
) -> tuple[DavrNatijasi, ...]:
    """Har bir davr uchun yopilgan natijani yig'adi."""
    hozir = hozir or datetime.now(UTC)
    natijalar = []

    for nom, kun in DAVRLAR.items():
        kesim = _kesim(hozir, kun)
        tanlangan = [
            q for q in qismlar if kesim is None or q.yopilgan_vaqt >= kesim
        ]
        jami = sum(q.natija_usd for q in tanlangan)
        natijalar.append(
            DavrNatijasi(
                nom=nom,
                realized_usd=jami,
                realized_pct=(jami / balans_usd * 100) if balans_usd > 0 else 0.0,
                savdo_soni=len({q.signal_id for q in tanlangan}),
            )
        )

    return tuple(natijalar)


def xulosa_qur(
    qismlar: list[YopilganQism],
    ochiqlar: list[OchiqPozitsiya],
    balans_usd: float,
    hozir: datetime | None = None,
) -> PnlXulosasi:
    """Dashboard uchun butun manzarani yig'adi.

    Unrealized ALOHIDA qaytadi va realized bilan qo'shilmaydi —
    3-promptning talabi. Sabab oddiy: ochiq savdoning "foydasi"
    hali pul emas, u bozor bilan birga o'zgaradi.
    """
    return PnlXulosasi(
        davrlar=realized_hisobla(qismlar, balans_usd, hozir),
        unrealized_usd=sum(p.unrealized_usd for p in ochiqlar),
        ochiq_soni=len(ochiqlar),
        balans_usd=balans_usd,
    )
