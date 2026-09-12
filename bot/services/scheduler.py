"""Fon vazifalari — takrorlanuvchi ishlar.

    obuna muddati       — soatda bir (1.2-band)
    veb signallari      — daqiqada bir, tarqatish uchun
    veb videolari       — 5 daqiqada bir

2026-09-03 — eski tahlil moduli olib tashlandi. U bilan birga signal
sikli, haftalik postmortem hisoboti va sayt uchun bozor ko'rinishi
vazifalari ham ketdi: uchalasi ham `core/analysis` ga tayanardi.

Halol ro'yxatni yangilash vazifasi ham chiqdi — u ro'yxatni FAQAT
o'sha sikl uchun xotirada tayyorlardi, hech qayerga yozmasdi. Halol
skrining modulining o'zi (`core/halal_screening/`) va admin
qarorlari (`CoinRulingRepository`) joyida qoldi.

Har bir vazifa MUSTAQIL: bittasining nosozligi boshqalarni to'xtatmaydi
(0.3-band). Shu sababli har biri o'z siklida, o'z `try/except` i bilan
ishlaydi.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta

from aiogram import Bot
from aiogram.types import FSInputFile

from bot.hosting import video_dir
from bot.i18n import DEFAULT_LANGUAGE, t
from bot.services.broadcast import broadcast_signal, obunachilar
from core.config.schema import AppConfig
from core.domain.enums import OrderType, SignalSource
from core.domain.models import EntryPlan, signal_levels
from core.market_data.binance import BinanceCandleProvider
from core.services import SubscriptionService
from core.services.signal_kuzatuvchi import SignalKuzatuvchi
from core.services.zanjir_sikl import ZanjirSikl
from core.storage import Database
from core.storage.repositories import (
    ContentRepository,
    PaymentRepository,
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger
from core.watch_panel.cmc_snapshot import CoinGeckoSurati
from core.watch_panel.coin_scanner import KuzatuvSkaneri
from core.watch_panel.live_market_data import BozorYigichi
from core.watch_panel.repository import KuzatuvRepository

logger = get_logger(__name__)

#: Rad etish sabablari shuncha kun saqlanadi. Admin paneli oxirgi 24 soatni
#: ko'rsatadi; bir hafta esa "kecha ham shunday edimi" savoliga yetadi.


async def _repeat(
    name: str,
    interval: timedelta,
    action: Callable[[], Awaitable[None]],
    initial_delay: timedelta | None = None,
) -> None:
    """Vazifani takrorlab turadi, xatolikda to'xtamaydi (0.3-band)."""
    if initial_delay is not None:
        await asyncio.sleep(initial_delay.total_seconds())

    while True:
        try:
            await action()
        except asyncio.CancelledError:
            logger.info("Fon vazifasi to'xtatildi: %s", name)
            raise
        except Exception:  # noqa: BLE001
            logger.exception("Fon vazifasi xato berdi: %s", name)
        await asyncio.sleep(interval.total_seconds())


def _manba(qiymat: str | None) -> SignalSource | None:
    """Bazadagi matnni `SignalSource` ga aylantiradi.

    Notanish qiymat `None` qaytaradi va kartochkada "eski modul"
    yorlig'i chiqadi. Bu ATAYLAB eng ehtiyotkor talqin: manbasi
    noma'lum signal ishonchli deb ko'rsatilmaydi.
    """
    if not qiymat:
        return None
    try:
        return SignalSource(qiymat)
    except ValueError:
        return None


class Scheduler:
    """Barcha fon vazifalarini boshqaradi."""

    def __init__(
        self,
        bot: Bot,
        database: Database,
        config: AppConfig,
        admin_ids: frozenset[int],
        candles: BinanceCandleProvider | None = None,
    ) -> None:
        self._bot = bot
        self._db = database
        self._config = config
        self._admin_ids = admin_ids
        # Provayder berilmasa zanjir sikli ISHGA TUSHMAYDI. Bu holat
        # `start()` da logga YOZILADI — aks holda bot ishlab turadi-yu
        # signal bermaydi, sababi esa noma'lum bo'lib qolardi.
        self._sikl = (
            ZanjirSikl(config, candles, database) if candles is not None else None
        )
        # KUZATUVCHI — narxni kuzatib signal holatini yangilaydi.
        # 2026-09-05 gacha bu umuman yo'q edi: hech bir signal "Faol"
        # bo'lmasdi, TP va Stop qayd etilmasdi, statistika to'lmasdi.
        self._kuzatuvchi = (
            SignalKuzatuvchi(config, candles, database) if candles is not None else None
        )
        # KUZATUV PANELI — signal modulidan MUSTAQIL (9-prompt).
        # U signal yozmaydi, faqat 80 coinning holatini yangilaydi.
        self._skaner = (
            KuzatuvSkaneri(config, candles, database) if candles is not None else None
        )
        # JONLI OQIM — FAQAT Top 20 uchun. Stakan va savdo lentasi
        # bu yerda YIG'ILMAYDI: ularni brauzer o'zi oladi. Bu yerda
        # faqat vaqt ichida to'planadigan narsa — xarid bosimi va
        # yirik savdolar (9-prompt, 6-qism).
        self._yigich = BozorYigichi(
            config.market_data, config.halal_screening.quote_asset
        )
        self._surat = CoinGeckoSurati(config.market_data)
        #: Jonli yozuvlar sanog'i — CoinGecko har 20-yozuvda so'raladi.
        self._jonli_hisob = 0
        self._video_dir = video_dir()
        self._tasks: list[asyncio.Task] = []

    def start(self) -> None:
        """Barcha vazifalarni fon rejimida ishga tushiradi."""
        vazifalar = [
            ("subscriptions", timedelta(hours=1), self._check_subscriptions, timedelta(minutes=2)),
            # Veb-panelda yaratilgan signallar shu vazifa orqali hayotga
            # kiradi. Oraliq qisqa: signal yozilgandan keyin obunachiga
            # yetguncha o'tgan har bir daqiqa — narx harakatlangan daqiqa.
            (
                "web-signals",
                timedelta(minutes=1),
                self._pickup_web_signals,
                timedelta(seconds=20),
            ),
            # Saytga yuklangan video darsliklarni Telegramga chiqarish.
            # Oraliq uzunroq: dars — kunlar davomida yashaydigan kontent,
            # signal kabi daqiqasiga bog'liq emas. Har yuklash bir necha
            # yuz megabaytlik yuborish demak, tez-tez urinish shart emas.
            (
                "web-videos",
                timedelta(minutes=5),
                self._pickup_web_videos,
                timedelta(minutes=1),
            ),
        ]

        if self._sikl is not None:
            # Sikl YOQILGANINI admin BILISHI kerak. 2026-09-04 da
            # admin signal olib, uni qaysi modul berganini ajrata
            # olmadi. Endi modul ishga tushganda ham xabar boradi,
            # signalda ham yorliq turadi.
            self._tasks.append(
                asyncio.create_task(self._sikl_yoqildi_xabari(), name="zanjir-xabar")
            )
            # ZANJIR SIKLI — yangi tahlil moduli.
            #
            # Kechikish 3 daqiqa: bot endi ko'tarilganda birjaga
            # o'nlab so'rov yuborish eng yomon payt. Avval obuna va
            # veb vazifalari o'tsin.
            vazifalar.append((
                "zanjir",
                timedelta(hours=self._config.zanjir.sikl_soat),
                self._zanjir_sikli,
                timedelta(minutes=3),
            ))
            # KUZATUV — signal sikldan TEZ-TEZ yuradi.
            #
            # Sikl 4 soatda bir marta YANGI signal qidiradi; kuzatuv
            # esa MAVJUD signallarni oldinga suradi. Narx TP yoki
            # Stopga tegishi uchun 4 soat kutish — foydalanuvchi
            # botda eskirgan holatni ko'rishi demak.
            #
            # 5 daqiqa: kuzatuv timeframei 15 daqiqa, ya'ni undan
            # tez-tez tekshirish yangi ma'lumot bermaydi, lekin
            # yopilgan sham darrov o'qiladi.
            vazifalar.append((
                "kuzatuv",
                timedelta(minutes=5),
                self._signallarni_kuzat,
                timedelta(minutes=1),
            ))
            # KUZATUV PANELI SKANI — 80 coin, signal bermaydi.
            #
            # Kechikish 6 daqiqa: zanjir sikli (3 daqiqa) bilan bir
            # paytda yugursa, ikkalasi birjaga bir zumda yuzlab
            # so'rov yuborardi. Ular bir xil coinlarni o'qiydi,
            # lekin turli timeframeda — kesh yordam bermaydi.
            vazifalar.append((
                "kuzatuv-skan",
                timedelta(hours=self._config.kuzatuv.skan_soat),
                self._kuzatuv_skani,
                timedelta(minutes=6),
            ))
            # ADMIN SO'ROVI — "hozir yangila" tugmasi.
            #
            # Sayt bazaga bayroq qo'yadi, bu vazifa uni ko'radi.
            # Daqiqada bir marta: admin tugmani bosgach javobni
            # uzoq kutmasin.
            vazifalar.append((
                "kuzatuv-sorov",
                timedelta(minutes=1),
                self._kuzatuv_sorovi,
                timedelta(seconds=30),
            ))
            # JONLI YIG'MANI BAZAGA YOZISH.
            #
            # 30 soniya: xarid bosimi 15 daqiqalik oyna ustida
            # hisoblanadi, ya'ni u sekundiga sezilarli o'zgarmaydi.
            # Tez-tez yozish bazaga bekorga urish bo'lardi.
            vazifalar.append((
                "kuzatuv-jonli",
                timedelta(seconds=30),
                self._jonli_yigma,
                timedelta(minutes=7),
            ))
            # Oqimning o'zi — vazifa emas, uzluksiz ishlaydigan jarayon.
            self._tasks.append(
                asyncio.create_task(self._yigich.yur(), name="kuzatuv-oqim")
            )
        else:
            logger.warning(
                "Zanjir sikli O'CHIQ: sham provayderi berilmagan. "
                "Bot ishlaydi, lekin AVTOMATIK signal bermaydi."
            )

        for nom, oraliq, harakat, kechikish in vazifalar:
            vazifa = asyncio.create_task(
                _repeat(nom, oraliq, harakat, kechikish), name=nom
            )
            self._tasks.append(vazifa)

        logger.info("Fon vazifalari ishga tushdi: %d ta", len(self._tasks))

    async def _kuzatuv_skani(self) -> None:
        """80 coinni skanlaydi. SIGNAL YOZMAYDI.

        Xato bo'lsa u bazaga yoziladi va admin panelda ko'rinadi —
        aks holda panel eski ma'lumot bilan turaverar va hech kim
        sababini bilmasdi.
        """
        if self._skaner is None:
            return
        async with self._db.session() as session:
            await KuzatuvRepository(session).boshlandi()
        try:
            natija = await self._skaner.yur()
        except Exception as xato:  # noqa: BLE001 — holat ekranda ko'rinsin
            logger.exception("Kuzatuv skani yiqildi")
            async with self._db.session() as session:
                await KuzatuvRepository(session).xato(str(xato))
            return
        async with self._db.session() as session:
            await KuzatuvRepository(session).tugadi(
                tekshirildi=natija.tekshirildi,
                otdi=natija.royxatlar.jami_korinadi if natija.royxatlar else 0,
            )

        # JONLI OQIM RO'YXATI — skandan KEYIN yangilanadi. Top 20
        # o'zgargan bo'lsa, chiqqan coinlar uzilib, yangilari
        # ulanadi.
        top = [n.symbol for n in (natija.royxatlar.top if natija.royxatlar else ())]
        self._yigich.kuzat(top)
        async with self._db.session() as session:
            await KuzatuvRepository(session).bozordan_tashqarilarni_ochir(top)

    async def _jonli_yigma(self) -> None:
        """Top 20 ning jonli yig'masini bazaga yozadi.

        CoinGecko so'rovi HAR SAFAR yuborilmaydi — u sekin
        o'zgaradigan ma'lumot (kapitalizatsiya) beradi va bepul
        chegarasi bor. Har 20-yozuvda, ya'ni taxminan 10 daqiqada
        bir marta so'raladi.
        """
        yigmalar = self._yigich.barchasi()
        if not yigmalar:
            return

        self._jonli_hisob += 1
        suratlar: dict[str, object] = {}
        if self._jonli_hisob % 20 == 1:
            suratlar = dict(await self._surat.ol([y.symbol for y in yigmalar]))

        async with self._db.session() as session:
            repo = KuzatuvRepository(session)
            for yigma in yigmalar:
                await repo.bozorni_yoz(yigma, suratlar.get(yigma.symbol))  # type: ignore[arg-type]

    async def _kuzatuv_sorovi(self) -> None:
        """Admin "hozir yangila" bosdimi — bosgan bo'lsa skan yuradi."""
        if self._skaner is None:
            return
        async with self._db.session() as session:
            sorov = await KuzatuvRepository(session).sorov_bormi()
        if sorov:
            logger.info("Kuzatuv skani ADMIN so'rovi bilan boshlanmoqda")
            await self._kuzatuv_skani()

    async def stop(self) -> None:
        # Oqim va HTTP sessiyasi ALOHIDA yopiladi: `cancel()` ularni
        # yopmaydi va bot to'xtaganda ochiq soket qolib ketardi.
        self._yigich.yopil()
        for vazifa in self._tasks:
            vazifa.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        await self._surat.yop()

    # ------------------------------------------------------------------ #


    async def _check_subscriptions(self) -> None:
        """1.2-band: muddati tugaganlarni yopish va eslatma yuborish."""
        async with self._db.session() as session:
            xizmat = SubscriptionService(
                self._config.subscriptions,
                UserRepository(session),
                SubscriptionRepository(session),
                PaymentRepository(session),
            )
            await xizmat.expire_overdue()

            eslatmalar = await xizmat.due_reminders()
            yuboriladiganlar = []
            for obuna, qolgan_kun in eslatmalar:
                from core.storage.models import User

                egasi = await session.get(User, obuna.user_id)
                if egasi is not None:
                    yuboriladiganlar.append((egasi.telegram_id, qolgan_kun))
                xizmat.mark_reminder_sent(obuna, qolgan_kun)

        for telegram_id, qolgan_kun in yuboriladiganlar:
            try:
                await self._bot.send_message(
                    telegram_id,
                    t("obuna.eslatma", DEFAULT_LANGUAGE, days=qolgan_kun),
                )
            except Exception:  # noqa: BLE001
                logger.warning("Eslatma yetkazilmadi: telegram_id=%s", telegram_id)

    async def _sikl_yoqildi_xabari(self) -> None:
        """Bot ko'tarilganda adminga "modul yoqildi" deb aytadi."""
        z = self._config.zanjir
        if not z.avtomatik_signal:
            # TO'XTATILGAN HOLAT JIM O'TMASIN. Admin har safar
            # bot ko'tarilganda buni ko'rishi kerak — aks holda
            # "nega signal kelmayapti" degan savol tug'ilardi va
            # javob kodning ichida qolib ketardi.
            await self._adminlarga(
                "⛔ <b>Avtomatik signal TO'XTATILGAN</b>\n\n"
                f"Zanjir moduli har <b>{z.sikl_soat} soatda</b> "
                f"<b>{len(z.kuzatiladigan_coinlar)}</b> ta coinni "
                "tekshirishda davom etadi va natijani yozadi — "
                "lekin SIGNAL YOZILMAYDI.\n\n"
                "Sabab: to'rtta mustaqil o'lchov signallar zarar "
                "keltirishini ko'rsatdi "
                "(<code>docs/BACKTEST_NATIJA_2026-09-10_model2.md</code>).\n\n"
                "Mavjud ochiq signallar odatdagidek kuzatiladi.\n"
                "Admin panelidan QO'LDA signal yozish ishlaydi."
            )
            return
        matn = (
            "🤖 <b>Zanjir moduli ishga tushdi</b>\n\n"
            f"Har <b>{z.sikl_soat} soatda</b> tekshiradi\n"
            f"Kuzatilayotgan coinlar: <b>{len(z.kuzatiladigan_coinlar)}</b> ta\n"
            f"{', '.join(z.kuzatiladigan_coinlar)}\n\n"
            "Bundan keyingi avtomatik signallarda "
            "«🤖 Zanjir moduli» yorlig'i bo'ladi.\n"
            "Yorliqsiz yoki «🕰 Eski modul» yozuvli signal — "
            "ESKI ma'lumot, unga ishonmang."
        )
        await self._adminlarga(matn)

    async def _adminlarga(self, matn: str) -> None:
        """Xabar yetmasa sikl to'xtamaydi — sabab logga yoziladi."""
        for admin_id in self._admin_ids:
            try:
                await self._bot.send_message(admin_id, matn)
            except Exception:  # noqa: BLE001 — bitta admin yetmasligi jiddiy emas
                logger.warning("Adminga xabar yetmadi: %s", admin_id)

    async def _signallarni_kuzat(self) -> None:
        """Ochiq signallarni narx bilan oldinga suradi.

        Bu vazifa 2026-09-05 da qo'shildi. Undan oldin signal holati
        UMUMAN yangilanmasdi: hammasi abadiy "Kutilmoqda" bo'lib
        turardi, TP va Stop qayd etilmasdi, statistika to'lmasdi.

        Kuzatuv XABAR YUBORMAYDI. Holat o'zgarishi botda va saytda
        keyingi ochilishda ko'rinadi. Har TP uchun alohida xabar
        yuborish alohida qaror — u foydalanuvchini bezovta qilishi
        mumkin va uni loyiha egasi hal qiladi.
        """
        if self._kuzatuvchi is None:
            return
        await self._kuzatuvchi.yur()

    async def _zanjir_sikli(self) -> None:
        """Yangi tahlil modulini yuritadi va topilgan signalni yozadi.

        Yozilgan signal shu yerda TARQATILMAYDI — uni bir daqiqadan
        keyin `_pickup_web_signals` oladi. Sabab: kartochka har bir
        obunachi uchun alohida yasaladi va o'sha mantiq bitta joyda
        turishi kerak.
        """
        if self._sikl is None:
            return
        natija = await self._sikl.yur()
        if natija.avtomatik_ochiq:
            # HAMMA TEKSHIRUVDAN O'TDI, LEKIN YOZILMADI.
            # Admin buni bilishi kerak: bu tizim hech narsa
            # topmagani emas — topdi, biz to'xtatdik.
            await self._adminlarga(
                f"⛔ <b>{natija.avtomatik_ochiq} ta coin hamma tekshiruvdan o'tdi</b>\n"
                "Avtomatik signal o'chiq — yozilmadi."
            )
        if not natija.yangi_signallar:
            return

        nomlar = ", ".join(symbol for symbol, _ in natija.yangi_signallar)
        logger.info(
            "Zanjir sikli %d ta yangi signal yozdi: %s",
            len(natija.yangi_signallar), nomlar,
        )
        await self._adminlarga(
            f"🤖 <b>Zanjir moduli {len(natija.yangi_signallar)} ta signal topdi</b>\n"
            f"{nomlar}\n\n"
            "Obunachilarga bir daqiqa ichida yuboriladi."
        )

    async def _pickup_web_signals(self) -> None:
        """Veb-panelda yaratilgan signallarni kuzatuvga oladi va tarqatadi.

        Nima uchun bu ish botda: kartochka HAR BIR obunachi uchun alohida
        yasaladi (miqdor uning balansidan hisoblanadi, 5.1-band) va
        `protect_content=True` bilan yuboriladi. Buni veb tomonda
        takrorlash — kartochka mantig'ining ikkinchi nusxasi demak edi.
        Shuning uchun veb faqat BAZAGA YOZADI, yuborish esa shu yerda.

        KUZATUV HOZIRCHA YO'Q: `watcher.py` eski holat mashinasi bilan
        birga olib tashlandi. Signal tarqatiladi, lekin TP/Stop
        avtomatik kuzatilmaydi — yangi modul kelguncha buni admin
        qo'lda belgilaydi.
        """
        async with self._db.session() as session:
            kutayotganlar = await SignalRepository(session).pending_broadcast()
            if not kutayotganlar:
                return
            tayyor = [
                (
                    y.id,
                    y.symbol,
                    signal_levels(entry=y.entry, stop=y.stop, tp1=y.tp1, tp2=y.tp2),
                    OrderType(y.entry_order_type),
                    _manba(y.source),
                )
                for y in kutayotganlar
            ]
            qabul_qiluvchilar = await obunachilar(session)

        for signal_id, symbol, levels, buyurtma, manba in tayyor:
            reja = EntryPlan(order_type=buyurtma, reference_price=levels.entry)
            yuborildi = await broadcast_signal(
                self._bot, qabul_qiluvchilar, symbol, levels, reja,
                signal_id, self._config, manba=manba,
            )
            async with self._db.session() as session:
                await SignalRepository(session).mark_broadcast(signal_id)
            logger.info(
                "Veb-paneldagi signal tarqatildi: id=%s symbol=%s -> %d ta",
                signal_id, symbol, yuborildi,
            )

    async def _pickup_web_videos(self) -> None:
        """Saytga yuklangan video darsliklarni Telegramga chiqaradi.

        NIMA UCHUN KERAK: sayt video faylni doimiy diskka yozadi va uni
        o'zi o'ynatadi. Bot esa faylni yo'ldan emas, Telegram `file_id`
        dan yuboradi — `file_id` faqat fayl BIR MARTA Telegramga
        yuborilganda paydo bo'ladi.

        Bu qadam bo'lmasa, saytdan qo'shilgan dars botda ko'rinmay
        qolardi: bitta ro'yxat ikki joyda ikki xil bo'lib qolardi.

        Fayl adminning shaxsiy chatiga yuboriladi — bu texnik yuborish,
        maqsadi faqat `file_id` olish. Admin yo'q bo'lsa qadam
        o'tkazib yuboriladi va dars faqat saytda qoladi (bu — xato
        emas, shunchaki sozlanmagan holat).
        """
        if not self._admin_ids:
            return

        qabul_qiluvchi = min(self._admin_ids)
        async with self._db.session() as session:
            kutayotganlar = await ContentRepository(session).pending_upload()
            tayyor = [(k.id, k.title, k.video_path) for k in kutayotganlar]

        for content_id, sarlavha, nom in tayyor:
            if not nom:
                continue
            yol = self._video_dir / nom
            if not yol.exists():
                logger.warning(
                    "Dars videosi diskda yo'q: id=%s fayl=%s", content_id, nom
                )
                continue
            try:
                xabar = await self._bot.send_video(
                    qabul_qiluvchi,
                    FSInputFile(yol),
                    caption=f"🎬 {sarlavha}\n\n(texnik yuborish — Telegram nusxasi tayyorlanmoqda)",
                    protect_content=True,
                )
            except Exception:  # noqa: BLE001
                # Sabab har xil bo'lishi mumkin: fayl juda katta, tarmoq
                # uzildi, Telegram cheklovi. Keyingi urinishda qayta
                # sinaladi — yozuv o'zgarmagani uchun ro'yxatda qoladi.
                logger.warning(
                    "Dars videosi Telegramga chiqmadi: id=%s", content_id, exc_info=True
                )
                continue

            if xabar.video is None:
                logger.warning("Javobda video yo'q: id=%s", content_id)
                continue

            async with self._db.session() as session:
                await ContentRepository(session).set_file_id(
                    content_id, xabar.video.file_id
                )
            logger.info(
                "Dars videosi Telegramga chiqdi: id=%s sarlavha=%s", content_id, sarlavha
            )
