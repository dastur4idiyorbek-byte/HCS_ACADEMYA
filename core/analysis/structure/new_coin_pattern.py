"""Yangi coinlar (<90 kun) uchun soddalashtirilgan struktura naqshi.

2-prompt, 1-qism va 4-qism (BLOK 2 oxiri):

    birinchi Swing High -> korreksiya -> o'sha darajani qayta sinab
    yuqoriga BOS

NIMA UCHUN ALOHIDA: yangi coinda HH/HL ketma-ketligi uchun yetarli
tarix yo'q. To'liq blokni qo'llash bunday coinlarni HAR DOIM 0/4
qilardi — ya'ni ular umuman signal bermasdi. Bu "ehtiyotkorlik"
emas, ko'r nuqta: yangi coinlarda eng katta harakatlar bo'ladi.

PASTROQ ISHONCH bilan o'tkaziladi: naqsh topilsa 2 ta ichki
tekshiruv ✅ beriladi (4 tadan emas) — struktura bloki eng ko'pi
bilan 2/2 chiqadi va ishonch formulasida shunga yarasha turadi.
"""

from __future__ import annotations

from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.domain.models import Candle

#: Korreksiya birinchi cho'qqidan kamida shu foizga tushishi kerak.
#: 🔴 O'LCHANMAGAN. Kichik tebranishni "korreksiya" deb o'qimaslik uchun.
KORREKSIYA_ENG_KAM_PCT = 5.0


def yangi_coin_naqshi(shamlar: list[Candle], nuqtalar: list[Swing]) -> bool:
    """Naqsh topildimi: cho'qqi -> korreksiya -> qayta sinab BOS.

    Uch qadam KETMA-KET tekshiriladi. Tartib buzilsa naqsh yo'q:
    masalan korreksiyasiz to'g'ridan-to'g'ri o'sish — bu boshqa
    holat (parabolik harakat), va unga kirish xavfli.
    """
    yuqorilar = [s for s in nuqtalar if s.turi is SwingTuri.YUQORI]
    if not yuqorilar:
        return False

    choqqi = yuqorilar[0]
    keyingi = shamlar[choqqi.indeks + 1 :]
    if not keyingi:
        return False

    # 1-qadam: korreksiya — cho'qqidan sezilarli pastga tushish
    eng_past = min(sham.low for sham in keyingi)
    tushish_pct = (choqqi.narx - eng_past) / choqqi.narx * 100
    if tushish_pct < KORREKSIYA_ENG_KAM_PCT:
        return False

    # 2-qadam: qayta sinov — narx cho'qqi darajasiga QAYTGAN
    # 3-qadam: BOS — va uni YOPILISH bilan kesib o'tgan
    #
    # Ikkalasi bitta shartda: korreksiyadan KEYIN yopilish cho'qqidan
    # yuqori bo'lsa, narx u yerga qaytgan ham, kesib o'tgan ham.
    tushish_indeksi = next(
        i for i, sham in enumerate(keyingi) if sham.low == eng_past
    )
    return any(sham.close > choqqi.narx for sham in keyingi[tushish_indeksi + 1 :])
