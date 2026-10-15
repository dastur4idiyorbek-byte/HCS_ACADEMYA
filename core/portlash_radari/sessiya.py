"""Bitta radar sessiyasi: manba -> darvoza -> elak -> 7 tekshiruv -> o'rin -> baza.

OQIM (`docs/MODUL_4_0_0.md`, 4-6-bo'lim):

    1. Juftliklar, ticker, funding — hamma symbol uchun ommaviy so'rov
    2. Hajm darvozasi ($500k) va elak (30 kunlik o'rtachadan 3x)
       + tasdiqlash (B) sessiyasida shu shamning A nomzodlari ham
    3. Elakdan o'tganlarga kapitalizatsiya darvozasi ($10 mln) —
       ma'lumot faqat shular uchun so'raladi
    4. Nazorat guruhi (namuna) — elakdan o'tmaganlardan
    5. Coin boshiga OI va long/short — faqat pool + namuna
    6. 7 tekshiruv, sanoq, holat, o'rin, ketma-ket
    7. "chiqdi" — oldingi rasmiy sessiyada o'rin olgan, endi yo'q coinlar
       narxi (sessiya jadvalidagi foiz uchun)

HAR SESSIYA NOLDAN. Oldingi sessiyadan faqat ikki narsa o'qiladi:
A nomzodlari (TASDIQLANGAN belgisi uchun) va qo'shni sessiyaning
"ketma-ket" soni (faqat ma'lumot). Ikkalasi ham sanoqqa va o'ringa
ta'sir qilmaydi — tasdiqlangan belgisi o'rindagi teng holatni ajratadi,
xolos.

QAT'IY CHEGARA: bu yerda hech qanday narx darajasi (Entry/Stop/TP)
hisoblanmaydi. Yozilgan narx — "o'sha sessiyadagi narx", tavsiya emas.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from core.config.schema import AppConfig
from core.portlash_radari.belgi import symboldan_asosiy
from core.portlash_radari.halol import Reestr, bazadagi_qarorlar
from core.portlash_radari.manba import (
    BinanceFutures,
    CoinGeckoTaminot,
    Juftlik,
    ManbaJurnali,
    Taminot,
    narx_mosmi,
)
from core.portlash_radari.repository import TUGADI, XATO, RadarRepository
from core.portlash_radari.sozlama import Chegaralar, chegaralar_qur
from core.portlash_radari.tartib import (
    TASDIQLANGAN,
    TartibKirishi,
    elakdan_otadimi,
    holat,
    ketma_ket,
    namuna_tanla,
    orinlar,
    yangi_listingmi,
)
from core.portlash_radari.tekshiruvlar import (
    STANDART_FUNDING_SOAT,
    CoinMalumoti,
    hammasi,
    sana,
)
from core.portlash_radari.vaqt import (
    KASHFIYOT,
    RASMIY_TURLAR,
    TASDIQ,
    kun_va_tartib,
    oldingi_rasmiy_slot,
)
from core.storage import Database
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)

#: Himoya: kesh buzilgan bo'lsa elak yuzlab coinni o'tkazib yuborib,
#: Binance'ga yuzlab so'rov yubormasin. Sog'lom holatda pool 20-30 ta.
MAX_POOL = 120

ELAK = "elak"
NAMUNA = "namuna"
CHIQDI = "chiqdi"


class UnlockManbasi(Protocol):
    async def jadval(self) -> dict: ...


class RadarXatosi(RuntimeError):
    """Sessiyani davom ettirib bo'lmaydi (masalan ticker kelmadi)."""


@dataclass(frozen=True, slots=True)
class SessiyaXulosasi:
    sessiya_id: int
    holat: str
    elakdan: int = 0
    nomzod: int = 0
    izoh: str = ""


@dataclass
class _Meta:
    nisbat: float | None
    yangi: bool
    ortacha: float | None
    kunlar: int


class RadarSessiyasi:
    def __init__(
        self,
        config: AppConfig,
        database: Database,
        binance: BinanceFutures,
        coingecko: CoinGeckoTaminot,
        unlock: UnlockManbasi,
        soat: Callable[[], datetime] = utc_now,
    ) -> None:
        self._config = config
        self._db = database
        self._b = binance
        self._cg = coingecko
        self._u = unlock
        self._soat = soat

    async def yur(self, turi: str, sham_vaqti: datetime) -> SessiyaXulosasi:
        """Sessiyani yurgizadi. Xato bo'lsa sessiya `xato` bilan yopiladi
        va xulosa qaytadi — istisno tashqariga chiqmaydi."""
        hozir = self._soat()
        kun, tartib = kun_va_tartib(sham_vaqti)
        async with self._db.session() as s:
            repo = RadarRepository(s)
            ch, ogohlar = chegaralar_qur(self._config.radar, await repo.sozlamalar())
            sessiya_id = await repo.sessiya_boshla(
                turi, sham_vaqti, kun, tartib, ch.lugat(), hozir
            )

        jurnal = ManbaJurnali()
        try:
            xulosa = await self._hisobla(sessiya_id, turi, sham_vaqti, ch, ogohlar, jurnal)
        except asyncio.CancelledError:
            await self._xato_bilan_yop(sessiya_id, jurnal, "sessiya bekor qilindi")
            raise
        except Exception as xato:  # noqa: BLE001 — xato ekranda ko'rinsin
            logger.exception("Radar sessiyasi yiqildi: %s %s", turi, sham_vaqti)
            await self._xato_bilan_yop(sessiya_id, jurnal, str(xato) or type(xato).__name__)
            return SessiyaXulosasi(sessiya_id, XATO, izoh=str(xato))
        return xulosa

    async def _xato_bilan_yop(self, sessiya_id: int, jurnal: ManbaJurnali, izoh: str) -> None:
        async with self._db.session() as s:
            await RadarRepository(s).sessiya_yakunla(
                sessiya_id, holat=XATO, tugadi=self._soat(), manbalar=jurnal.lugat(), izoh=izoh
            )

    async def _hisobla(
        self,
        sessiya_id: int,
        turi: str,
        sham_vaqti: datetime,
        ch: Chegaralar,
        ogohlar: list[str],
        jurnal: ManbaJurnali,
    ) -> SessiyaXulosasi:
        hozir = self._soat()

        # --- 1. Ommaviy so'rovlar ------------------------------------- #
        juftliklar = await self._b.juftliklar(jurnal)
        if not juftliklar:
            raise RadarXatosi(_manba_xatosi("juftliklar ro'yxati", jurnal))
        tickerlar = await self._b.tickerlar(jurnal)
        if not tickerlar:
            raise RadarXatosi(_manba_xatosi("24 soatlik ticker", jurnal))
        fundinglar = await self._b.funding_stavkalari(jurnal)
        oraliqlar = await self._b.funding_oraliqlari(jurnal)

        juft = {j.symbol: j for j in juftliklar}
        btc = tickerlar.get("BTCUSDT")
        btc_ozgarish = btc.ozgarish_24s if btc else None

        # --- Bazadan: kesh, yashirinlar, reestr, oldingi sessiyalar ---- #
        async with self._db.session() as s:
            repo = RadarRepository(s)
            ortachalar = await repo.ortachalar()
            yashirinlar = await repo.yashirinlar(hozir)
            reestr = Reestr(await bazadagi_qarorlar(s), self._config)

            a_nomzodlar: set[str] | None = None
            oldingi_orinli: set[str] = set()
            if turi == TASDIQ:
                a = await repo.tugagan_sessiya(KASHFIYOT, sham_vaqti)
                if a is not None:
                    a_nomzodlar = {
                        n.symbol for n in await repo.natijalar(a.id) if n.nomzod and n.turi == ELAK
                    }
                oldingi = await repo.oldingi_tasdiq(sham_vaqti)
                if oldingi is not None:
                    oldingi_orinli = {
                        n.symbol for n in await repo.natijalar(oldingi.id) if n.orin is not None
                    }

            oldingi_ketma: dict[str, int] = {}
            if turi in RASMIY_TURLAR:
                q_turi, q_sham = oldingi_rasmiy_slot(turi, sham_vaqti)
                qoshni = await repo.tugagan_sessiya(q_turi, q_sham)
                if qoshni is not None:
                    oldingi_ketma = {
                        n.symbol: n.ketma_ket for n in await repo.natijalar(qoshni.id) if n.nomzod
                    }

        # --- 2. Darvoza va elak --------------------------------------- #
        kesh_bor = bool(ortachalar)
        meta: dict[str, _Meta] = {}

        def meta_ol(j: Juftlik) -> _Meta:
            ortacha, kunlar = ortachalar.get(j.symbol, (None, 0))
            # Kesh umuman bo'sh bo'lsa "tarix yo'q" — HAMMA coin yangi
            # listing bo'lib qolardi. O'shanda faqat Binance sanasi ishlaydi.
            tarix = kunlar if (kesh_bor and j.symbol in ortachalar) else 10**6
            yangi = yangi_listingmi(j.onboard, hozir, tarix, ch)
            t = tickerlar.get(j.symbol)
            _, nisbat = elakdan_otadimi(t.hajm_24s if t else None, ortacha, kunlar, yangi, ch)
            # Yangi listing o'rtachasiz o'tadi va nisbati ham "noma'lum":
            # listing kunlaridagi sakrashga nisbat o'rin tartibini buzardi.
            return _Meta(None if yangi else nisbat, yangi, ortacha, kunlar)

        darvozadan = 0
        pool: list[str] = []
        qolgan: list[str] = []
        for j in juftliklar:
            t = tickerlar.get(j.symbol)
            if t is None or t.hajm_24s is None or t.hajm_24s < ch.min_hajm_24s_usd:
                continue
            darvozadan += 1
            m = meta[j.symbol] = meta_ol(j)
            otdi = (m.nisbat is not None and m.nisbat >= ch.elak_hajm_x) or m.yangi
            (pool if otdi else qolgan).append(j.symbol)

        # B sessiyasi A nomzodlarini QAYTA tekshiradi — ular elakdan
        # tushgan bo'lsa ham (`docs/MODUL_4_0_0.md`, 6-bo'lim).
        for symbol in sorted(a_nomzodlar or ()):
            if symbol in juft and symbol in tickerlar and symbol not in pool:
                meta.setdefault(symbol, meta_ol(juft[symbol]))
                pool.append(symbol)
                if symbol in qolgan:
                    qolgan.remove(symbol)

        if len(pool) > MAX_POOL:
            ogohlar.append(f"pool {len(pool)} ta edi, {MAX_POOL} tasi olindi (kesh tekshirilsin)")
            pool.sort(key=lambda s: (-(meta[s].nisbat or 0.0), s))
            pool = pool[:MAX_POOL]

        # --- 3-4. Kapitalizatsiya darvozasi va namuna ------------------- #
        # Rasmiy sessiya uchun urug' faqat shamdan: qayta hisoblansa ham
        # o'sha coinlar. Qo'lda tekshiruvda vaqt ham qo'shiladi.
        urug = f"{turi}:{sham_vaqti.isoformat()}"
        if turi not in RASMIY_TURLAR:
            urug += f":{hozir.isoformat()}"
        namuna_nomzodi = namuna_tanla(
            [s for s in qolgan if s not in oldingi_orinli], ch.namuna_soni * 2, urug
        )
        taminotlar = await self._cg.ol(
            {juft[s].belgi for s in pool + namuna_nomzodi}, jurnal
        )

        def taminot(symbol: str) -> Taminot | None:
            j = juft[symbol]
            ta = taminotlar.get(j.belgi)
            t = tickerlar.get(symbol)
            if ta is None or not narx_mosmi(ta, t.narx if t else None, j.kopaytirgich):
                return None
            return ta

        def kapdan_otadimi(symbol: str) -> bool:
            # Noma'lum kapitalizatsiya CHETLATMAYDI — bilmaslik coinni
            # tozalab ham, chiqarib ham qo'ymaydi.
            ta = taminot(symbol)
            if ta is None or ta.market_cap is None:
                return True
            return ta.market_cap >= ch.min_kapitalizatsiya_usd

        pool = [s for s in pool if kapdan_otadimi(s)]
        namuna = [s for s in namuna_nomzodi if kapdan_otadimi(s)][: ch.namuna_soni]

        # --- 5. Coin boshiga so'rovlar ---------------------------------- #
        chuqur = pool + namuna
        oi_lar = await asyncio.gather(
            *(self._b.oi_tarixi(s, ch.oi_oyna_soat, jurnal) for s in chuqur)
        )
        ls_lar = await asyncio.gather(*(self._b.long_short(s, jurnal) for s in chuqur))
        unlocklar = await self._unlock_jadvali(jurnal)

        # --- 6. Tekshiruvlar ------------------------------------------ #
        qatorlar: dict[str, dict] = {}
        tartib_kirishlari: list[TartibKirishi] = []
        for symbol, oi_qator, ls in zip(chuqur, oi_lar, ls_lar, strict=True):
            j = juft[symbol]
            t = tickerlar[symbol]
            m = meta[symbol]
            ta = taminot(symbol)
            u = unlocklar.get(j.belgi)
            coin = CoinMalumoti(
                symbol=symbol,
                belgi=j.belgi,
                narx=t.narx,
                ozgarish_24s=t.ozgarish_24s,
                hajm_24s=t.hajm_24s,
                ortacha_30k=m.ortacha,
                tarix_kunlar=m.kunlar,
                funding_stavka=fundinglar.get(symbol),
                funding_oraliq_soat=oraliqlar.get(symbol, STANDART_FUNDING_SOAT),
                oi_qatorlar=oi_qator,
                long_short=ls,
                btc_ozgarish=btc_ozgarish,
                aylanma_pct=ta.aylanma_pct if ta else None,
                unlock_kun=getattr(u, "kun_qoldi", None),
                unlock_pct=getattr(u, "pct", None),
                yangi_listing=m.yangi,
            )
            tekshiruvlar = hammasi(coin, ch)
            sanoq = sana(tekshiruvlar)
            nomzod = sanoq.tasdiq >= ch.nomzod_min
            turi_qator = ELAK if symbol in pool else NAMUNA
            a_nomzodmi = None if a_nomzodlar is None else symbol in a_nomzodlar
            coin_holati = holat(turi, nomzod, a_nomzodmi)
            yashirin = symbol in yashirinlar
            qatorlar[symbol] = {
                "symbol": symbol,
                "belgi": j.belgi,
                "turi": turi_qator,
                "narx": t.narx,
                "hajm_24s": t.hajm_24s,
                "hajm_nisbati": None if m.nisbat is None else round(m.nisbat, 4),
                "ozgarish_24s": t.ozgarish_24s,
                "market_cap": ta.market_cap if ta else None,
                "tekshiruvlar_json": json.dumps(
                    [x.lugat() for x in tekshiruvlar], ensure_ascii=False
                ),
                "tasdiq_soni": sanoq.tasdiq,
                "harakat_soni": sanoq.harakat,
                "yoqilgi_soni": sanoq.yoqilgi,
                "malumot_yoq_soni": sanoq.malumot_yoq,
                "nomzod": nomzod,
                "holat": coin_holati,
                "orin": None,
                "ketma_ket": (
                    ketma_ket(turi, nomzod, oldingi_ketma.get(symbol))
                    if turi_qator == ELAK
                    else 0
                ),
                "yashirin": yashirin,
                "yangi_listing": m.yangi,
                "halol": reestr.holati(j.belgi),
            }
            if turi_qator == ELAK and not yashirin:
                tartib_kirishlari.append(
                    TartibKirishi(
                        symbol=symbol,
                        tasdiq_soni=sanoq.tasdiq,
                        tasdiqlangan=coin_holati == TASDIQLANGAN,
                        yoqilgi_soni=sanoq.yoqilgi,
                        hajm_nisbati=m.nisbat,
                    )
                )

        for symbol, orin in orinlar(tartib_kirishlari).items():
            qatorlar[symbol]["orin"] = orin

        # --- 7. "chiqdi" — faqat narx ---------------------------------- #
        for symbol in sorted(oldingi_orinli - set(qatorlar)):
            t = tickerlar.get(symbol)
            j = juft.get(symbol)
            qatorlar[symbol] = {
                "symbol": symbol,
                "belgi": j.belgi if j else symboldan_asosiy(symbol),
                "turi": CHIQDI,
                "narx": t.narx if t else None,
                "hajm_24s": t.hajm_24s if t else None,
                "ozgarish_24s": t.ozgarish_24s if t else None,
                "halol": reestr.holati(j.belgi if j else symboldan_asosiy(symbol)),
            }

        nomzodlar = sum(
            1 for q in qatorlar.values() if q["turi"] == ELAK and q.get("nomzod")
        )
        async with self._db.session() as s:
            repo = RadarRepository(s)
            await repo.natijalarni_yoz(sessiya_id, list(qatorlar.values()))
            await repo.sessiya_yakunla(
                sessiya_id,
                holat=TUGADI,
                tugadi=self._soat(),
                manbalar=jurnal.lugat(),
                universum=len(juftliklar),
                darvozadan=darvozadan,
                elakdan=len(pool),
                nomzod=nomzodlar,
                btc_ozgarish=btc_ozgarish,
                izoh="; ".join(ogohlar),
            )

        logger.info(
            "Radar %s %s: universum=%d darvoza=%d elak=%d nomzod=%d",
            turi, sham_vaqti.isoformat(), len(juftliklar), darvozadan, len(pool), nomzodlar,
        )
        return SessiyaXulosasi(sessiya_id, TUGADI, elakdan=len(pool), nomzod=nomzodlar)

    async def _unlock_jadvali(self, jurnal: ManbaJurnali) -> dict:
        """DefiLlama unlock kalendari — `UnlockManba` dan FAQAT O'QILADI.

        U xatoda bo'sh lug'at qaytaradi va kodni aytmaydi; bo'sh javob
        manba holatida "xato" bo'lib yoziladi.
        """
        try:
            jadval = await self._u.jadval()
        except Exception:  # noqa: BLE001 — unlocksiz ham 6 tekshiruv ishlaydi
            logger.exception("Unlock kalendari olinmadi")
            jadval = {}
        if jadval:
            jurnal.yoz("unlock", 200)
        else:
            jurnal.yoz("unlock", None, "bo'sh javob")
        return {str(k).upper(): v for k, v in jadval.items()}


def _manba_xatosi(nima: str, jurnal: ManbaJurnali) -> str:
    if jurnal.cheklangan():
        return (
            f"Binance {nima}ni bermadi: 451 — server mintaqasi Binance Futures "
            "tomonidan cheklangan"
        )
    return f"Binance {nima}ni bermadi"

