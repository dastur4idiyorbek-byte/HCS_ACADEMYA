"""1-qism: balansni bo'laklarga bo'lish va signalga kapital ajratish.

QOIDA (3-prompt, 1-qism):

    Balans N ta TENG bo'lakka bo'linadi (N — config, boshlang'ich 3).
    Har bir bo'lak MUSTAQIL va o'zining ichki zarar chegarasiga ega
    (bo'lakning O'ZIDAN hisoblanadi, umumiy balansdan emas).

    Signal kelganda bo'sh bo'lak qidiriladi:

        Stop% <= chegara   ->  bo'lakning to'lig'i ishlatiladi
        Stop% >  chegara   ->  ulush = chegara / Stop%

    Ishlatilmagan qism SHU BO'LAK ichida bo'sh qoladi va keyingi
    signal uni olishi mumkin.

    Barcha bo'laklar band bo'lsa — signal KUTADI.

NIMA UCHUN SOF FUNKSIYALAR. Bu yerda baza ham, tarmoq ham yo'q:
kirish — bo'laklar ro'yxati, chiqish — yangi ro'yxat. Shu sababli
mantiqni bazasiz sinash mumkin va u tahlil modulidan mustaqil
qoladi (3-promptning asosiy sharti).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

#: Bo'lakning ichki zarar chegarasi, foizda (bo'lakning O'ZIDAN).
STANDART_CHEGARA_PCT = 10.0

#: Shundan kichik pozitsiya ochilmaydi.
#:
#: Birjada minimal savdo hajmi bor (odatda 5-10$). Undan kichik
#: "pozitsiya" — hisobda bor, bozorda yo'q narsa. Bunday yozuv
#: statistikani jimgina buzardi.
ENG_KAM_MIQDOR_USD = 5.0


@dataclass(frozen=True, slots=True)
class Bolak:
    """Balansning bitta bo'lagi va uning band qismi."""

    raqam: int
    hajm: float
    #: Ochiq pozitsiyalarga ketgan pul.
    band_kapital: float = 0.0
    #: O'sha pozitsiyalarda XAVF ostidagi pul (Stop ursa yo'qoladi).
    band_xavf: float = 0.0

    @property
    def bosh_kapital(self) -> float:
        return max(0.0, self.hajm - self.band_kapital)

    @property
    def band(self) -> bool:
        """Bo'lakda yangi pozitsiya uchun joy qoldimi."""
        return self.bosh_kapital < ENG_KAM_MIQDOR_USD

    @property
    def xavf_pct(self) -> float:
        """Bo'lakning necha foizi xavf ostida."""
        return 0.0 if self.hajm <= 0 else self.band_xavf / self.hajm * 100


@dataclass(frozen=True, slots=True)
class Taqsimot:
    """Bitta signalga ajratilgan kapital."""

    bolak_raqami: int
    miqdor_usd: float
    xavf_usd: float
    stop_masofa_pct: float
    #: Bo'lakning to'lig'i ishlatildimi (Stop% chegaradan kichik edi).
    toliq_bolak: bool

    @property
    def izoh(self) -> str:
        if self.toliq_bolak:
            return f"{self.bolak_raqami}-bo'lak to'liq"
        return f"{self.bolak_raqami}-bo'lakning bir qismi (Stop {self.stop_masofa_pct:.1f}%)"


def bolaklarni_yarat(balans: float, soni: int = 3) -> list[Bolak]:
    """Balansni teng bo'laklarga bo'ladi."""
    if balans <= 0:
        raise ValueError("Balans musbat bo'lishi kerak")
    if soni < 1:
        raise ValueError("Bo'lak soni kamida 1 bo'lishi kerak")
    hajm = balans / soni
    return [Bolak(raqam=i + 1, hajm=hajm) for i in range(soni)]


def joylashtir(
    bolaklar: list[Bolak],
    stop_masofa_pct: float,
    chegara_pct: float = STANDART_CHEGARA_PCT,
) -> Taqsimot | None:
    """Signalga bo'lak topadi va miqdorni hisoblaydi.

    Returns:
        `Taqsimot`, yoki `None` — bo'sh bo'lak yo'q (signal KUTADI).
    """
    if stop_masofa_pct <= 0:
        raise ValueError("Stop masofasi musbat bo'lishi kerak")

    for bolak in bolaklar:
        if bolak.band:
            continue

        # Chegaradan kichik Stop — bo'lakning to'lig'i ishlatiladi.
        # Kattasi — ulush kamayadi, natijada XAVF baribir chegarada
        # qoladi: (hajm x chegara/stop) x stop = hajm x chegara.
        ulush = min(1.0, chegara_pct / stop_masofa_pct)
        kerakli = bolak.hajm * ulush
        miqdor = min(kerakli, bolak.bosh_kapital)

        if miqdor < ENG_KAM_MIQDOR_USD:
            continue

        return Taqsimot(
            bolak_raqami=bolak.raqam,
            miqdor_usd=miqdor,
            xavf_usd=miqdor * stop_masofa_pct / 100,
            stop_masofa_pct=stop_masofa_pct,
            toliq_bolak=ulush >= 1.0,
        )

    return None


def band_qil(bolaklar: list[Bolak], taqsimot: Taqsimot) -> list[Bolak]:
    """Taqsimotni bo'laklar holatiga yozadi."""
    return [
        replace(
            b,
            band_kapital=b.band_kapital + taqsimot.miqdor_usd,
            band_xavf=b.band_xavf + taqsimot.xavf_usd,
        )
        if b.raqam == taqsimot.bolak_raqami
        else b
        for b in bolaklar
    ]


def bosat(
    bolaklar: list[Bolak],
    bolak_raqami: int,
    miqdor_usd: float,
    xavf_usd: float,
) -> list[Bolak]:
    """Pozitsiya yopilganda bo'lakni bo'shatadi.

    Manfiy holatga tushmaydi: qayta bo'shatish (masalan xabar ikki
    marta kelsa) bo'lakni "manfiy band" qilib qo'ymasligi kerak.
    """
    return [
        replace(
            b,
            band_kapital=max(0.0, b.band_kapital - miqdor_usd),
            band_xavf=max(0.0, b.band_xavf - xavf_usd),
        )
        if b.raqam == bolak_raqami
        else b
        for b in bolaklar
    ]


def umumiy_xavf_pct(bolaklar: list[Bolak]) -> float:
    """Butun balansning necha foizi hozir xavf ostida.

    NIMA UCHUN BU FUNKSIYA BOR. 3-prompt bitta kafolat beradi:
    "hamma bo'lak band bo'lib, hammasi Stop ursa — umumiy zarar
    ~10%". Bu kafolat bo'lakda BITTA pozitsiya bo'lganda to'g'ri.

    Lekin o'sha promptning o'zi ishlatilmagan qismni keyingi
    signalga berishga ruxsat beradi — ya'ni bo'lakda ikkita
    pozitsiya bo'lishi mumkin va o'shanda bo'lakning xavfi
    chegaradan oshadi.

    Shuning uchun raqam TAXMIN QILINMAYDI — shu yerda o'lchanadi
    va foydalanuvchiga ochiq ko'rsatiladi.
    """
    jami_hajm = sum(b.hajm for b in bolaklar)
    if jami_hajm <= 0:
        return 0.0
    return sum(b.band_xavf for b in bolaklar) / jami_hajm * 100
