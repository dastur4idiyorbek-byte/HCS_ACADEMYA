"""JONLI SIKL — yangi zanjir modulini haqiqiy bozorda yuritadi.

Backtest o'tmishni qayta o'ynatardi. Bu modul aynan o'sha
mantiqni HOZIRGI narxda yuritadi va signal topsa bazaga yozadi.

TARQATISH BU YERDA EMAS. Sikl faqat `signals` jadvaliga yozadi;
obunachilarga yuborishni mavjud `_pickup_web_signals` vazifasi
bajaradi. Ansiz kartochka yasash mantig'ining ikkinchi nusxasi
paydo bo'lardi.

BACKTEST BILAN BIR XIL MANTIQ. Sikl `zanjir_yur` va
`darajalar_qur` funksiyalarini AYNAN backtest chaqirgandek
chaqiradi. Agar bu yerda boshqacha chaqirilsa, jonli natija
o'lchangan natijaga mos kelmasdi — va biz buni bilmasdik.

FUNDAMENTAL BLOK. Backtestda u bo'sh edi (tarixiy manba yo'q).
Jonli tizimda ham hozircha bo'sh: manbalar ulanmagan. Blok
"o'lchanmadi" holatida turadi va zanjirni UZMAYDI. Manba
ulanganda bu yerga qo'shiladi va signal soni KAMAYADI —
qanchaga, noma'lum (`GIPOTEZA_DAFTARI.md`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.analysis.ai_verification.ai_verifier import AiTekshiruvKirish, ai_tekshir
from core.analysis.alternatives.alternative_chain import zanjir_yur_alternativ
from core.analysis.chain.block_chain_engine import ZanjirKirish
from core.analysis.structure.swing_detector import swinglar
from core.analysis.zone_quality.order_block import ObTarifi
from core.config.schema import AppConfig
from core.domain.enums import SignalSource
from core.domain.models import Candle, signal_levels
from core.market_data.binance import BinanceCandleProvider
from core.position.entry_stop_tp import darajalar_qur
from core.services.kirish_rejasi import decide_entry_plan
from core.storage.database import Database
from core.storage.repositories import SignalRepository
from core.storage.zanjir_repository import (
    BlokHolati,
    CoinHolati,
    ZanjirHolatRepository,
)
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Necha sham so'raladi. Backtestdagi `ASOSIY_OYNA`/`PASTKI_OYNA`
#: bilan BIR XIL — aks holda indikatorlar boshqa oynada
#: hisoblanib, jonli qaror o'lchangan qarordan farq qilardi.
ASOSIY_OYNA = 500
PASTKI_OYNA = 500


@dataclass
class SiklNatijasi:
    """Bitta yugurishning hisoboti — "nega signal yo'q" uchun."""

    tekshirildi: int = 0
    ochiq_sababli_otkazildi: int = 0
    yangi_signallar: list[tuple[str, int]] = field(default_factory=list)
    uzilishlar: dict[str, int] = field(default_factory=dict)
    daraja_radlari: dict[str, int] = field(default_factory=dict)
    xatolar: dict[str, str] = field(default_factory=dict)

    def matn(self) -> str:
        qatorlar = [
            f"Tekshirildi: {self.tekshirildi} coin",
            f"Yangi signal: {len(self.yangi_signallar)}",
        ]
        if self.ochiq_sababli_otkazildi:
            qatorlar.append(
                f"Ochiq signali bor: {self.ochiq_sababli_otkazildi} coin o'tkazildi"
            )
        for nom, soni in sorted(self.uzilishlar.items(), key=lambda x: -x[1]):
            qatorlar.append(f"   zanjir uzildi — {nom}: {soni}")
        for nom, soni in sorted(self.daraja_radlari.items(), key=lambda x: -x[1]):
            qatorlar.append(f"   daraja rad etildi — {nom}: {soni}")
        for symbol, sabab in self.xatolar.items():
            qatorlar.append(f"   ⚠️ {symbol}: {sabab}")
        return "\n".join(qatorlar)


class ZanjirSikl:
    """Zanjirni jonli bozorda yuritadi."""

    def __init__(
        self,
        config: AppConfig,
        provider: BinanceCandleProvider,
        database: Database,
    ) -> None:
        self._config = config
        self._provider = provider
        self._db = database

    async def yur(self) -> SiklNatijasi:
        z = self._config.zanjir
        natija = SiklNatijasi()

        async with self._db.session() as session:
            ochiq = {y.symbol.upper() for y in await SignalRepository(session).open_signals()}

        btc = await self._shamlar("BTC", z.timeframelar.asosiy, ASOSIY_OYNA)

        holatlar: list[CoinHolati] = []
        for symbol in z.kuzatiladigan_coinlar:
            symbol = symbol.upper()
            if symbol in ochiq:
                # BIR COINDA IKKITA SIGNAL BO'LMAYDI. Backtest ham
                # shunday ishlaydi — aks holda jonli natija
                # o'lchangandan ko'p savdo berardi.
                natija.ochiq_sababli_otkazildi += 1
                holatlar.append(
                    CoinHolati(
                        symbol=symbol,
                        bloklar=(),
                        toliq=False,
                        uzildi_blokda=None,
                        ishonch=0.0,
                        natija="ochiq_signal",
                        izoh="ochiq signali bor — tekshirilmadi",
                    )
                )
                continue
            try:
                holat = await self._bitta_coin(symbol, btc, natija)
            except Exception as xato:  # noqa: BLE001 — bitta coin butun siklni to'xtatmasin
                natija.xatolar[symbol] = f"{type(xato).__name__}: {xato}"
                logger.exception("Zanjir sikli: %s tekshirilmadi", symbol)
                holat = CoinHolati(
                    symbol=symbol,
                    bloklar=(),
                    toliq=False,
                    uzildi_blokda=None,
                    ishonch=0.0,
                    natija="xato",
                    izoh=f"{type(xato).__name__}: {xato}",
                )
            if holat is not None:
                holatlar.append(holat)

        await self._holatlarni_yoz(holatlar)

        logger.info("Zanjir sikli tugadi:\n%s", natija.matn())
        return natija

    async def _holatlarni_yoz(self, holatlar: list[CoinHolati]) -> None:
        """Ekran uchun holatni bazaga yozadi — BIR TOMONLAMA oqim.

        Yozuv SIKLNI TO'XTATMASLIGI kerak: bu ma'lumot faqat
        ko'rsatish uchun, signal esa allaqachon yaratilgan. Baza
        bilan muammo bo'lsa, ekran eskiroq holatni ko'rsatadi —
        lekin signal yo'qolmaydi.
        """
        if not holatlar:
            return
        try:
            async with self._db.session() as session:
                repo = ZanjirHolatRepository(session)
                for holat in holatlar:
                    await repo.yoz(holat)
        except Exception:  # noqa: BLE001 — ko'rsatish uchun ma'lumot, signal emas
            logger.exception("Zanjir holatlari yozilmadi (ekran eskiroq bo'ladi)")

    async def _bitta_coin(
        self, symbol: str, btc: list[Candle], natija: SiklNatijasi
    ) -> CoinHolati | None:
        """Bitta coinni tekshiradi va EKRAN uchun holatini qaytaradi.

        Holat qaytariladi, shu yerda YOZILMAYDI: yozish `yur()` da,
        bitta sessiyada. Ansiz har coin uchun alohida tranzaksiya
        ochilardi.
        """
        z = self._config.zanjir
        shamlar = await self._shamlar(symbol, z.timeframelar.asosiy, ASOSIY_OYNA)
        if len(shamlar) < 30:  # noqa: PLR2004
            natija.xatolar[symbol] = "sham yetarli emas"
            return CoinHolati(
                symbol=symbol,
                bloklar=(),
                toliq=False,
                uzildi_blokda=None,
                ishonch=0.0,
                natija="xato",
                izoh="sham yetarli emas",
            )

        natija.tekshirildi += 1
        narx = shamlar[-1].close

        natijasi = zanjir_yur_alternativ(
            ZanjirKirish(
                symbol=symbol,
                shamlar=shamlar,
                pastki_shamlar=await self._shamlar(
                    symbol, z.timeframelar.tasdiq, PASTKI_OYNA
                ),
                btc_shamlar=btc,
                etalon=symbol == "BTC",
                ob_tarifi=ObTarifi(z.bloklar.ob_tarifi),
                unlock_yaqin_kun=z.bloklar.unlock_yaqin_kun,
                unlock_katta_pct=z.bloklar.unlock_katta_pct,
            )
        )
        zanjir = natijasi.zanjir
        bloklar = _blok_holatlari(zanjir)

        def holat(turi: str, izoh: str = "", signal_id: int | None = None) -> CoinHolati:
            return CoinHolati(
                symbol=symbol,
                bloklar=bloklar,
                toliq=zanjir.toliq,
                uzildi_blokda=zanjir.uzildi_blokda,
                ishonch=zanjir.ishonch(),
                natija=turi,
                izoh=izoh,
                signal_id=signal_id,
            )

        if not zanjir.toliq:
            kalit = zanjir.uzildi_blokda or "nomalum"
            natija.uzilishlar[kalit] = natija.uzilishlar.get(kalit, 0) + 1
            return holat("zanjir_uzildi", f"uzildi: {kalit}")

        if zanjir.ishonch() < z.eng_kam_ishonch:
            natija.uzilishlar["ishonch"] = natija.uzilishlar.get("ishonch", 0) + 1
            return holat(
                "ishonch_past",
                f"ishonch {zanjir.ishonch():.2f} < {z.eng_kam_ishonch:.2f}",
            )

        zona = natijasi.zona_natija.zona if natijasi.zona_natija else None
        if zona is None:
            natija.daraja_radlari["zona yo'q"] = natija.daraja_radlari.get("zona yo'q", 0) + 1
            return holat("daraja_rad", "zona yo'q")

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
        )
        if not darajalar.yaroqli:
            sabab = _sabab_turi(darajalar.rad_sababi)
            natija.daraja_radlari[sabab] = natija.daraja_radlari.get(sabab, 0) + 1
            return holat("daraja_rad", darajalar.rad_sababi or sabab)

        levels = signal_levels(
            entry=darajalar.entry,
            stop=darajalar.stop,
            tp1=darajalar.tplar[0],
            tp2=darajalar.tplar[1] if len(darajalar.tplar) > 1 else None,
            tp3=darajalar.tplar[2] if len(darajalar.tplar) > 2 else None,  # noqa: PLR2004
        )
        reja = decide_entry_plan(narx, levels)
        if not reja.is_valid:
            # Narx zonadan CHIQIB ketgan — signal kech. Backtest bu
            # holatni "zona buzilgan" deb rad etardi, jonli tizim ham
            # rad etadi.
            natija.daraja_radlari["kech — narx zonadan chiqdi"] = (
                natija.daraja_radlari.get("kech — narx zonadan chiqdi", 0) + 1
            )
            return holat("daraja_rad", "kech — narx zonadan chiqdi")

        # 5-BLOK — SI tekshiruvi. Faqat 4 blok va darajalar o'tgandan
        # keyin ishga tushadi. Rad etsa signal YOZILMAYDI.
        ai_natija = await ai_tekshir(
            AiTekshiruvKirish(
                symbol=symbol,
                matn=zanjir.matn(),
                ishonch=zanjir.ishonch(),
                narx=narx,
            ),
            z.ai,
        )
        if not ai_natija.tasdiqlandi:
            natija.uzilishlar["SI"] = natija.uzilishlar.get("SI", 0) + 1
            return holat("ai_rad", ai_natija.sabab)

        async with self._db.session() as session:
            yozuv = await SignalRepository(session).create(
                symbol=symbol,
                levels=levels,
                source=SignalSource.ZANJIR,
                entry_plan=reja,
                note=zanjir.matn(),
                correlation_group=self._config.risk_engine.correlation_group_of(symbol),
            )
            signal_id = yozuv.id

        natija.yangi_signallar.append((symbol, signal_id))
        logger.info("ZANJIR SIGNAL: %s id=%s ishonch=%.2f", symbol, signal_id, zanjir.ishonch())
        return holat("signal", "signal berildi", signal_id)

    async def _shamlar(self, symbol: str, timeframe: str, oyna: int) -> list[Candle]:
        return await self._provider.fetch_candles(symbol, timeframe, oyna)


def _blok_holatlari(zanjir) -> tuple[BlokHolati, ...]:  # noqa: ANN001
    """Zanjir bloklarini ekran uchun tayyor holatga aylantiradi."""
    return tuple(
        BlokHolati(
            nom=b.nom,
            kuch=b.kuch,
            maxraj=b.maxraj,
            otdi=b.otdi,
            olchanmadi=b.olchanmadi,
            tosiq=b.qattiq_tosiq or "",
        )
        for b in zanjir.bloklar
    )


def _sabab_turi(sabab: str | None) -> str:
    """Rad sababidan raqamni olib tashlaydi — guruhlash uchun."""
    if not sabab:
        return "nomalum"
    return sabab.split(" (")[0]
