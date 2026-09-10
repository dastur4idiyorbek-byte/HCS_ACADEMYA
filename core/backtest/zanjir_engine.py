"""Yangi zanjirni tarixiy ma'lumotda qayta o'ynatadi.

ESKI ENGINE BILAN FARQI. Eski `engine.py` (1-promptda o'chirilgan)
butun jonli siklni — Risk Engine, sig'im, korrelyatsiya — qayta
yuritardi. Bu yerda ATAYLAB faqat ZANJIR o'lchanadi:

  Nima uchun: 16 o'lchov to'plami ko'rsatdiki, eski natijaning eng
  katta yo'qotishi STRATEGIYADA emas, SIG'IMDA edi — `risk_engine`
  4 668 nomzoddan 593 tasini o'tkazardi va sababning 87% i
  `max_open_signals` edi (`GIPOTEZA_DAFTARI.md`, audit 2-bosqichi).
  Ya'ni biz strategiyani emas, portfel chegarasini o'lchardik.

  Sig'im va korrelyatsiya JONLI tizimda qoladi (`core/risk_engine`),
  lekin zanjirning O'Z sifatini o'lchashda ular ARALASHMAYDI.

LOOKAHEAD HIMOYASI: `Dataset` har so'rovga vaqt chegarasi bilan
javob beradi. Bu yerda hech qanday `shamlar[-1]` dan keyingi
ma'lumot ishlatilmaydi.

XARAJAT: har savdoda 2 x (komissiya + sirg'anish) = 0.3%. Bu
model 1-promptdan o'zgarmasdan saqlandi — u to'g'ri ishlagan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.analysis.alternatives.alternative_chain import zanjir_yur_alternativ
from core.analysis.chain.block_chain_engine import ZanjirKirish, zanjir_yur
from core.analysis.fundamental.fundamental_block import FundamentalKirish
from core.analysis.structure.swing_detector import swinglar
from core.analysis.zone_quality.order_block import ObTarifi
from core.backtest.dataset import Dataset
from core.config.schema import AppConfig
from core.domain.models import Candle
from core.position.entry_stop_tp import darajalar_qur
from core.position.scaling_out import ChiqishRejasi, chiqish_rejasi, trailing_stop
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class Savdo:
    """Bitta yopilgan savdo."""

    symbol: str
    kirish_vaqti: datetime
    entry: float
    stop: float
    tplar: tuple[float, ...]
    chiqish_vaqti: datetime | None = None
    natija_pct: float = 0.0
    sabab: str = ""
    ushlash_soat: float = 0.0
    #: Nechta TP ga yetdi
    tp_soni: int = 0
    #: LIMIT hali bajarilmagan — narx `entry` ga tushishini kutmoqda.
    #:
    #: 2026-09-09 gacha bu maydon YO'Q edi va backtest savdoni darrov
    #: `entry` narxida ochardi — narx o'sha paytda entry'dan YUQORIDA
    #: bo'lsa ham. Ya'ni o'lchov bozor bermagan narxda sotib olgandek
    #: hisoblardi va limit umuman bajarilmasligi mumkinligini
    #: e'tiborga olmasdi.
    kutmoqda: bool = True
    #: Signal berilgan payt. `kirish_vaqti` dan farq qiladi: limit
    #: keyinroq bajariladi, muddat esa SIGNALDAN boshlanadi.
    signal_vaqti: datetime | None = None


@dataclass(slots=True)
class ZanjirNatijasi:
    nom: str
    qadamlar: int = 0
    savdolar: list[Savdo] = field(default_factory=list)
    #: Zanjir qaysi blokda necha marta uzildi
    uzilishlar: dict[str, int] = field(default_factory=dict)
    #: Zanjir to'liq bog'langan, lekin daraja rad etilgan holatlar
    daraja_radlari: dict[str, int] = field(default_factory=dict)
    #: Daraja ham tayyor bo'lgan, lekin PORTFEL chegarasi to'sgan
    #: holatlar (faqat `sigim=True` da to'ldiriladi)
    sigim_radlari: dict[str, int] = field(default_factory=dict)
    #: LIMIT bajarilmagan signallar — savdo umuman bo'lmagan.
    #:
    #: `savdolar` ga KIRMAYDI: bo'lmagan savdoni natijaga qo'shish
    #: o'lchovni yolg'on qilardi. Lekin sanaladi — aks holda "nega
    #: savdo kam" degan savolga javob yo'qolardi.
    bajarilmagan: dict[str, int] = field(default_factory=dict)
    #: ZAIFLIK HISOBOTI: har bir ichki tekshiruv necha marta
    #: HA / YOQ / MALUMOT_YOQ chiqqani.
    #:
    #: Ablatsiyadan BOSHQA savolga javob beradi. Ablatsiya
    #: "tekshiruvni olib tashlasa nima bo'ladi" deydi; bu esa
    #: "tekshiruv qanchalik tez-tez ijobiy chiqadi" deydi —
    #: ya'ni blokning qaysi qismi ZAIF ekanini ko'rsatadi.
    tekshiruv_holatlari: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def signal_soni(self) -> int:
        return len(self.savdolar)

    @property
    def foydali_pct(self) -> float:
        if not self.savdolar:
            return 0.0
        return sum(1 for s in self.savdolar if s.natija_pct > 0) / len(self.savdolar) * 100

    @property
    def profit_factor(self) -> float:
        foyda = sum(s.natija_pct for s in self.savdolar if s.natija_pct > 0)
        zarar = -sum(s.natija_pct for s in self.savdolar if s.natija_pct < 0)
        if zarar <= 0:
            return float("inf") if foyda > 0 else 0.0
        return foyda / zarar

    @property
    def ortacha_pct(self) -> float:
        if not self.savdolar:
            return 0.0
        return sum(s.natija_pct for s in self.savdolar) / len(self.savdolar)

    @property
    def jami_pct(self) -> float:
        return sum(s.natija_pct for s in self.savdolar)

    @property
    def eng_chuqur_pasayish(self) -> float:
        """Ketma-ket yig'ilgan natijaning cho'qqidan eng katta tushishi."""
        choqqi = 0.0
        yigindi = 0.0
        eng = 0.0
        for s in self.savdolar:
            yigindi += s.natija_pct
            choqqi = max(choqqi, yigindi)
            eng = max(eng, choqqi - yigindi)
        return eng


class ZanjirBacktest:
    """Zanjirni tarixda yuritadi va savdolarni simulyatsiya qiladi."""

    def __init__(
        self,
        config: AppConfig,
        nom: str = "zanjir",
        *,
        ochirilgan_tekshiruvlar: frozenset[str] = frozenset(),
        reja: ChiqishRejasi | None = None,
        sigim: bool = False,
        eng_kam_kuch: int = 1,
        alternativ: bool = False,
        nishon_tekshiruvi: bool = True,
    ) -> None:
        self._config = config
        self._nom = nom
        # SIG'IM: jonli tizimning portfel chegaralari (max_open_signals
        # va korrelyatsiya guruhi). Sukut bo'yicha O'CHIQ — zanjirning
        # O'Z sifati o'lchanayotganda ular aralashmasligi kerak
        # (fayl boshidagi izoh). Yoqilganda esa savol boshqa bo'ladi:
        # "shu strategiyadan REAL hisobda nechtasini olish mumkin?"
        self._sigim = sigim
        # BLOK QOIDASI. Sukut 1 — 2-promptning qoidasi. Boshqa
        # qiymat faqat `scripts/zanjir_blok_qoidasi.py` o'lchovida
        # beriladi; jonli tizim va boshqa o'lchovlar tegmaydi.
        self._eng_kam_kuch = eng_kam_kuch
        # ALTERNATIV ZANJIR: `zanjir_yur_alternativ` — zaif (1/N)
        # blokni alternativ yo'llar bilan qutqaradi.
        self._alternativ = alternativ
        # NISHON TEKSHIRUVI: "TP1 joriy narxdan yuqorimi".
        # Sukut YOQIQ — jonli tizim shunday ishlaydi. O'chirish faqat
        # o'lchov uchun: qoidaning natijaga ta'sirini ko'rish.
        self._nishon_tekshiruvi = nishon_tekshiruvi
        # ABLATSIYA uchun: nomi shu to'plamda bo'lgan ichki tekshiruv
        # `MALUMOT_YOQ` ga aylantiriladi, ya'ni maxrajdan chiqadi.
        self._ochirilgan = ochirilgan_tekshiruvlar
        self._reja = reja or chiqish_rejasi(
            trailing_yoqilgan=config.zanjir.chiqish.trailing_yoqilgan,
            trailing_r=config.zanjir.chiqish.trailing_r,
        )

    def yur(
        self,
        dataset: Dataset,
        symbols: list[str],
        max_qadam: int | None = None,
    ) -> ZanjirNatijasi:
        """Har bir asosiy sham yopilishida zanjirni tekshiradi."""
        z = self._config.zanjir
        natija = ZanjirNatijasi(nom=self._nom)
        ochiq: dict[str, Savdo] = {}

        vaqtlar = dataset.timeline(z.timeframelar.asosiy)
        if max_qadam is not None:
            vaqtlar = vaqtlar[-max_qadam:]

        for hozir in vaqtlar:
            natija.qadamlar += 1
            btc = _shamlar(dataset, "BTC", z.timeframelar.asosiy, hozir)
            nomzodlar: list[tuple[float, Savdo]] = []

            for symbol in symbols:
                shamlar = _shamlar(dataset, symbol, z.timeframelar.asosiy, hozir)
                if len(shamlar) < 30:
                    continue
                narx = shamlar[-1].close

                # 1) Ochiq savdoni yangilash — YANGI SIGNALDAN OLDIN.
                # Teskarisi bo'lsa bitta coinda ikkita savdo ochilardi.
                agar_ochiq = ochiq.get(symbol)
                if agar_ochiq is not None:
                    holat = self._yangila(agar_ochiq, shamlar[-1], hozir)
                    if holat == "yopildi":
                        natija.savdolar.append(agar_ochiq)
                        del ochiq[symbol]
                    elif holat == "bekor":
                        # Savdo BO'LMAGAN — natijaga kirmaydi.
                        sabab = agar_ochiq.sabab or "limit bajarilmadi"
                        natija.bajarilmagan[sabab] = (
                            natija.bajarilmagan.get(sabab, 0) + 1
                        )
                        del ochiq[symbol]
                    continue

                kirish = ZanjirKirish(
                    symbol=symbol,
                    shamlar=shamlar,
                    pastki_shamlar=_shamlar(
                        dataset, symbol, z.timeframelar.tasdiq, hozir, PASTKI_OYNA
                    ),
                    btc_shamlar=btc,
                    fundamental=FundamentalKirish(),
                    etalon=symbol.upper() == "BTC",
                    ob_tarifi=ObTarifi(z.bloklar.ob_tarifi),
                    ochirilgan=self._ochirilgan,
                    eng_kam_kuch=self._eng_kam_kuch,
                    unlock_yaqin_kun=z.bloklar.unlock_yaqin_kun,
                    unlock_katta_pct=z.bloklar.unlock_katta_pct,
                )
                natijasi = (
                    zanjir_yur_alternativ(kirish)
                    if self._alternativ
                    else zanjir_yur(kirish)
                )
                zanjir = natijasi.zanjir
                _holatlarni_yig(natija, zanjir)

                if not zanjir.toliq:
                    kalit = zanjir.uzildi_blokda or "nomalum"
                    natija.uzilishlar[kalit] = natija.uzilishlar.get(kalit, 0) + 1
                    continue

                if zanjir.ishonch() < z.eng_kam_ishonch:
                    natija.uzilishlar["ishonch"] = natija.uzilishlar.get("ishonch", 0) + 1
                    continue

                zona = natijasi.zona_natija.zona if natijasi.zona_natija else None
                if zona is None:
                    continue

                darajalar = darajalar_qur(
                    zona,
                    swinglar(shamlar),
                    narx,
                    eng_kam_stop_pct=z.darajalar.stop_eng_kam_pct,
                    eng_kop_stop_pct=z.darajalar.stop_eng_kop_pct,
                    eng_kam_nisbat=z.darajalar.tp1_eng_kam_nisbat,
                    eng_kop_tp=z.darajalar.tp_eng_kop,
                    eng_kam_oraliq_pct=z.darajalar.tp_eng_kam_oraliq_pct,
                    likvidlik_bufer_pct=z.darajalar.stop_likvidlik_bufer_pct,
                    nishon_narxdan_yuqori=self._nishon_tekshiruvi,
                )
                if not darajalar.yaroqli:
                    sabab = _sabab_turi(darajalar.rad_sababi)
                    natija.daraja_radlari[sabab] = natija.daraja_radlari.get(sabab, 0) + 1
                    continue

                nomzodlar.append((
                    zanjir.ishonch(),
                    Savdo(
                        symbol=symbol,
                        # Limit hali bajarilmagan: `kirish_vaqti`
                        # narx entry'ga TUSHGANDA qayta yoziladi.
                        kirish_vaqti=hozir,
                        signal_vaqti=hozir,
                        entry=darajalar.entry,
                        stop=darajalar.stop,
                        tplar=darajalar.tplar,
                    ),
                ))

            self._joylashtir(nomzodlar, ochiq, natija)

        # Oyna oxirida ochiq qolganlar joriy narxda yopiladi — aks
        # holda ular natijaga umuman kirmasdi va statistika faqat
        # "yopilgan" savdolardan iborat bo'lardi (omon qolish
        # tanlanmasi).
        for symbol, savdo in ochiq.items():
            if savdo.kutmoqda:
                # Limit oyna oxirigacha bajarilmadi — savdo bo'lmagan.
                natija.bajarilmagan["oyna tugadi — limit kutmoqda"] = (
                    natija.bajarilmagan.get("oyna tugadi — limit kutmoqda", 0) + 1
                )
                continue
            oxirgi = _shamlar(dataset, symbol, z.timeframelar.asosiy, vaqtlar[-1])
            if oxirgi:
                self._yop(savdo, oxirgi[-1].close, vaqtlar[-1], "oyna tugadi")
                natija.savdolar.append(savdo)

        return natija

    def _joylashtir(
        self,
        nomzodlar: list[tuple[float, Savdo]],
        ochiq: dict[str, Savdo],
        natija: ZanjirNatijasi,
    ) -> None:
        """Nomzodlarni ochiq savdolarga aylantiradi.

        `sigim` o'chiq bo'lsa — hammasi ochiladi (zanjirning O'Z
        sifati o'lchanadi).

        Yoqilganda jonli tizimning ikkita portfel qoidasi qo'llanadi:
        `max_open_signals` va korrelyatsiya guruhi. Bunda TARTIB
        muhim bo'lib qoladi: o'rin cheklangan bo'lsa, kim oldin
        kirishi kerak? Bu yerda ishonch bo'yicha eng kuchli nomzod
        oldin kiradi — jonli tizimdagi kabi. Alifbo tartibida
        olinsa, o'rinni doim "A" bilan boshlanadigan coin egallardi
        va natija coinlar ro'yxatining TARTIBIGA bog'liq bo'lib
        qolardi.
        """
        if not self._sigim:
            for _, savdo in nomzodlar:
                ochiq[savdo.symbol] = savdo
            return

        risk = self._config.risk_engine
        for _, savdo in sorted(nomzodlar, key=lambda n: n[0], reverse=True):
            if len(ochiq) >= risk.max_open_signals:
                natija.sigim_radlari["max_open_signals"] = (
                    natija.sigim_radlari.get("max_open_signals", 0) + 1
                )
                continue
            guruh = risk.correlation_group_of(savdo.symbol)
            if guruh is not None:
                band = sum(
                    1
                    for s in ochiq.values()
                    if risk.correlation_group_of(s.symbol) == guruh
                )
                if band >= risk.max_signals_per_correlation_group:
                    natija.sigim_radlari["korrelyatsiya"] = (
                        natija.sigim_radlari.get("korrelyatsiya", 0) + 1
                    )
                    continue
            ochiq[savdo.symbol] = savdo

    def _yangila(self, savdo: Savdo, sham: Candle, hozir: datetime) -> str:
        """Savdoni bitta sham bilan oldinga suradi.

        Returns:
            `""` — ochiq qoldi, `"yopildi"` — natijaga kiradi,
            `"bekor"` — limit bajarilmadi, savdo BO'LMAGAN.
        """
        z = self._config.zanjir.chiqish

        # --- LIMIT KUTMOQDA -----------------------------------------
        #
        # 2026-09-09 gacha bu bosqich YO'Q edi: backtest savdoni
        # darrov `entry` narxida ochardi, narx o'sha paytda entry'dan
        # yuqorida bo'lsa ham. Ya'ni o'lchov bozor bermagan narxda
        # sotib olgandek hisoblardi.
        #
        # Jonli misol (2026-09-05, LTC): entry 49.02, narx 50.23 edi
        # va 49.02 ga umuman tushmay TP1 (52.78) ga chiqdi. Backtestda
        # bu +7.67% lik G'ALABA bo'lib sanalardi — haqiqatda esa hech
        # narsa sotib olinmagan.
        #
        # Qoidalar JONLI KUZATUVCHI bilan bir xil
        # (`core/services/signal_kuzatuvchi.py`).
        if savdo.kutmoqda:
            if sham.low <= savdo.entry:
                savdo.kutmoqda = False
                # Muddat SIGNALDAN emas, KIRISHDAN hisoblanadi.
                savdo.kirish_vaqti = hozir
            elif savdo.tplar and sham.high >= savdo.tplar[0]:
                # Narx nishonga KIRILMASDAN yetdi — savdo bo'lmagan.
                savdo.sabab = "narx TP1 ga kirilmasdan yetdi"
                return "bekor"
            else:
                # Limit muddatsiz kutmasin: signal eskirsa, u endi
                # o'sha strukturaga tegishli emas.
                yosh = hozir - (savdo.signal_vaqti or savdo.kirish_vaqti)
                if yosh >= timedelta(days=z.umumiy_muddat_kun):
                    savdo.sabab = "limit muddati tugadi"
                    return "bekor"
                return ""

        # STOP AVVAL tekshiriladi. Bitta sham ichida ham TP, ham Stop
        # tegilgan bo'lsa, qaysi biri oldin bo'lganini BILMAYMIZ —
        # ehtiyotkor taxmin: Stop. Teskarisi natijani chiroyliroq
        # ko'rsatardi va bu — o'zini aldash.
        if sham.low <= savdo.stop:
            self._yop(savdo, savdo.stop, hozir, "stop")
            return "yopildi"

        for i, tp in enumerate(savdo.tplar):
            if sham.high >= tp and savdo.tp_soni <= i:
                savdo.tp_soni = i + 1
                if i == 0 and z.tp1_breakeven:
                    savdo.stop = savdo.entry

        if savdo.tp_soni >= len(savdo.tplar):
            self._yop(savdo, savdo.tplar[-1], hozir, "tp")
            return "yopildi"

        # Trailing — faqat TP2 dan keyingi qoldiqqa (yuqoridagi izoh)
        if savdo.tp_soni >= 2:
            yangi = trailing_stop(savdo.entry, savdo.stop, sham.high, self._reja)
            if yangi is not None:
                savdo.stop = yangi

        yosh = hozir - savdo.kirish_vaqti
        muddat = (
            timedelta(days=z.qoldiq_muddat_kun)
            if savdo.tp_soni > 0
            else timedelta(days=z.umumiy_muddat_kun)
        )
        if yosh >= muddat:
            self._yop(savdo, sham.close, hozir, "muddat")
            return "yopildi"

        return ""

    def _yop(self, savdo: Savdo, narx: float, vaqt: datetime, sabab: str) -> None:
        """Natijani XARAJAT bilan hisoblaydi.

        Qismli sotish hisobga olinadi: TP1 da 50%, TP2 da 30% va
        hokazo. Qolgan qism yopilish narxida sotiladi.
        """
        xarajat = 2 * (self._config.backtest.fee_pct + self._config.backtest.slippage_pct)
        tp_soni = len(savdo.tplar)

        yigindi = 0.0
        qolgan = 100.0
        for i in range(savdo.tp_soni):
            ulush = self._reja.ulush(i, tp_soni)
            yigindi += (savdo.tplar[i] - savdo.entry) / savdo.entry * 100 * ulush / 100
            qolgan -= ulush
        if qolgan > 0:
            yigindi += (narx - savdo.entry) / savdo.entry * 100 * qolgan / 100

        savdo.natija_pct = yigindi - xarajat
        savdo.chiqish_vaqti = vaqt
        savdo.sabab = sabab
        savdo.ushlash_soat = (vaqt - savdo.kirish_vaqti).total_seconds() / 3600


#: Asosiy timeframeda necha sham ko'riladi.
#:
#: Jonli tizim ham cheklangan oyna bilan ishlaydi — birjadan butun
#: tarix so'ralmaydi. Chegarasiz qoldirilsa ikki narsa buziladi:
#: (1) backtest jonlidan BOSHQA oynani ko'radi, (2) har qadamda ish
#: hajmi o'sib boradi, ya'ni O(n²).
ASOSIY_OYNA = 500

#: Pastki timeframeda necha sham ko'riladi.
#:
#: 500 × 15 daqiqa ≈ 5 kun. 4.2 tasdig'iga shuncha yetadi: u zona
#: ICHIDAGI mini-BOS ni qidiradi, ya'ni yaqin o'tmish.
#:
#: Chegarasiz qoldirilganda 730 kunlik sinovda bu qator har qadamda
#: ~89 000 shamgacha o'sardi va o'lchov soatlab yurardi.
PASTKI_OYNA = 500


def _holatlarni_yig(natija: ZanjirNatijasi, zanjir) -> None:  # noqa: ANN001
    """Har bir tekshiruvning holatini sanaydi.

    MAXRAJ HAR XIL. Zanjir uzilganda keyingi bloklar UMUMAN
    hisoblanmaydi, ya'ni 4-blokdagi tekshiruv 2-blokdagidan kamroq
    marta ko'riladi. Shuning uchun hisobotda har bir tekshiruvning
    O'Z jami ko'rsatiladi — foizlarni umumiy qadam soniga bo'lish
    yolg'on natija berardi.
    """
    for blok in zanjir.bloklar:
        for t in blok.tekshiruvlar:
            hisob = natija.tekshiruv_holatlari.setdefault(
                t.nom, {"ha": 0, "yoq": 0, "malumot_yoq": 0}
            )
            hisob[t.holat.value] += 1


def _sabab_turi(sabab: str | None) -> str:
    """Rad sababidan RAQAMNI olib tashlaydi — guruhlash uchun.

    Ansiz har bir rad alohida kalit bo'lardi: "stop juda yaqin
    (2.60%)", "stop juda yaqin (1.29%)" va hokazo. Natijada voronka
    o'nlab "1 × ..." qatoriga aylanib, hech narsa ko'rsatmasdi —
    aynan tashxis qo'yish kerak bo'lgan joyda.
    """
    if not sabab:
        return "nomalum"
    return sabab.split(" (")[0]


def _shamlar(
    dataset: Dataset,
    symbol: str,
    timeframe: str,
    hozir: datetime,
    oyna: int = ASOSIY_OYNA,
) -> list[Candle]:
    """Lookaheadsiz kesim, CHEGARALANGAN oyna bilan."""
    seriya = dataset.series.get(symbol)
    if seriya is None:
        return []
    return seriya.up_to(timeframe, hozir, limit=oyna)
