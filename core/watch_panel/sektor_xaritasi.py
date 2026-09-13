"""Coin -> sektor xaritasi (CoinGecko kategoriya identifikatori).

--------------------------------------------------------------------
NEGA XARITA QO'LDA YOZILGAN
--------------------------------------------------------------------

CoinGecko coinning kategoriyasini `/coins/{id}` da beradi — ya'ni
COIN BOSHIGA bitta so'rov. 80 coin uchun bu har skanda 80 qo'shimcha
so'rov degani va bepul planning tezlik chegarasini yorib yuboradi.

Kategoriyalar esa deyarli o'zgarmaydi: SOL bugun ham, bir yildan
keyin ham "smart contract platform". Shuning uchun xarita bir marta
yozildi va so'rovda faqat KATEGORIYA NATIJASI olinadi
(`/coins/categories` — bitta so'rov, hamma kategoriya).

--------------------------------------------------------------------
XATO YOZILGAN IDENTIFIKATOR NIMA QILADI
--------------------------------------------------------------------

HECH NARSANI BUZMAYDI. Kategoriya topilmasa `sektor_kuchli` `None`
bo'ladi va tekshiruv MALUMOT_YOQ beradi — "sektor zaif" EMAS.
Skaner esa topilmagan identifikatorlarni LOG ga yozadi, shunda
admin qaysi qatorni tuzatish kerakligini ko'radi (`coin_scanner`
dagi "Sektor xaritasi" xabari).

Ya'ni bu xarita "to'g'ri bo'lishi SHART" emas — u qancha to'g'ri
bo'lsa, shuncha ko'p coin sektor ma'lumotiga ega bo'ladi, xolos.

--------------------------------------------------------------------

QAT'IY CHEGARA: bu faylda Entry/Stop/TP hisoblanmaydi.
"""

from __future__ import annotations

#: Symbol -> CoinGecko kategoriya identifikatori.
#:
#: IDENTIFIKATORLAR O'YLAB TOPILMAGAN. Ularning hammasi
#: `web/src/lib/sektorlar.ts` dagi `KORSATILADIGAN_SEKTORLAR`
#: ro'yxatidan olingan — o'sha ro'yxat bozor ko'rinishi sahifasida
#: allaqachon ishlaydi, ya'ni bu identifikatorlar CoinGecko
#: javobida BOR ekani amalda tasdiqlangan.
#:
#: Test buni qulflaydi: xaritaga o'sha ro'yxatda yo'q identifikator
#: yozilsa, `test_kuzatuv_sektor_unlock.py` yiqiladi.
#:
#: Bitta coin bir nechta kategoriyaga kirishi mumkin (masalan POL
#: ham "layer-2", ham "layer-1"). Bu yerda ENG XARAKTERLI bittasi
#: tanlangan: sektor rotatsiyasi "pul qaysi guruhga oqyapti" degan
#: savolga javob beradi, va coin odatda o'zining asosiy guruhi
#: bilan birga harakatlanadi.
#:
#: BA'ZI COINLAR XARITADA YO'Q — ATAYLAB. STEEM, HIVE, TWT, BAT,
#: EDU, AVA kabi coinlar uchun tasdiqlangan ro'yxatda mos guruh
#: yo'q. Ularni zo'rlab birortasiga tiqish — noto'g'ri ma'lumot
#: berish. Xaritada yo'q coin `sektor_kuchli=None` oladi, ya'ni
#: MALUMOT_YOQ: "sektori zaif" EMAS, "bilmaymiz".
SEKTOR: dict[str, str] = {
    # --- Layer 1 zanjirlar ------------------------------------------
    #
    # PoW pul coinlari (BTC, BCH, LTC, DGB, RVN, XEC) ham shu yerda:
    # tasdiqlangan ro'yxatda "Proof of Work" ataylab yo'q — u
    # texnologiya, sektor emas (`sektorlar.ts` izohi). Ular baribir
    # o'z zanjiriga ega L1 tarmoqlar.
    "BTC": "layer-1",
    "BCH": "layer-1",
    "LTC": "layer-1",
    "DGB": "layer-1",
    "RVN": "layer-1",
    "XEC": "layer-1",
    "ETH": "layer-1",
    "SOL": "layer-1",
    "ADA": "layer-1",
    "AVAX": "layer-1",
    "NEAR": "layer-1",
    "ETC": "layer-1",
    "APT": "layer-1",
    "SUI": "layer-1",
    "HBAR": "layer-1",
    "ALGO": "layer-1",
    "EGLD": "layer-1",
    "S": "layer-1",
    "FLOW": "layer-1",
    "MINA": "layer-1",
    "CKB": "layer-1",
    "ZIL": "layer-1",
    "CELO": "layer-1",
    "XTZ": "layer-1",
    "QTUM": "layer-1",
    "NEO": "layer-1",
    "ICX": "layer-1",
    "ONT": "layer-1",
    "ASTR": "layer-1",
    "STRAX": "layer-1",
    "QKC": "layer-1",
    "IOST": "layer-1",
    "XLM": "layer-1",
    "IOTA": "layer-1",
    "VET": "layer-1",
    # Modulli zanjirlar — alohida guruh, lekin tasdiqlangan
    # ro'yxatda yo'q. Ular ham o'z qatlamiga ega L1 lar.
    "TIA": "layer-1",
    "DYM": "layer-1",
    "SAGA": "layer-1",
    # --- Layer 2 va masshtablash ------------------------------------
    "POL": "layer-2",
    "OP": "layer-2",
    "ARB": "layer-2",
    "IMX": "layer-2",
    "STRK": "layer-2",
    "STX": "layer-2",
    # --- O'zaro bog'lanish -------------------------------------------
    "DOT": "interoperability",
    "ATOM": "interoperability",
    "KSM": "interoperability",
    "MOVR": "interoperability",
    "ONE": "interoperability",
    "RIF": "interoperability",
    # --- Orakullar ----------------------------------------------------
    "LINK": "oracle",
    "PYTH": "oracle",
    "API3": "oracle",
    "TRB": "oracle",
    # --- Sun'iy intellekt ---------------------------------------------
    "TAO": "artificial-intelligence",
    "RENDER": "artificial-intelligence",
    # --- Saqlash ------------------------------------------------------
    "FIL": "storage",
    "AR": "storage",
    "STORJ": "storage",
    "SC": "storage",
    # --- DePIN (jismoniy infratuzilma tarmoqlari) ---------------------
    "THETA": "depin",
    "TFUEL": "depin",
    "JASMY": "depin",
    # --- Infratuzilma --------------------------------------------------
    "GRT": "infrastructure",
    "CTSI": "infrastructure",
    "BICO": "infrastructure",
    "ACH": "infrastructure",
    "MASK": "infrastructure",
    "PHA": "infrastructure",
    "REQ": "infrastructure",
    "HOT": "infrastructure",
    # --- Identifikatsiya -----------------------------------------------
    "CVC": "identity",
    # --- O'yin ---------------------------------------------------------
    "CHR": "gaming",
    # --- NFT ------------------------------------------------------------
    "RARE": "non-fungible-tokens-nft",
}


def slug(matn: str) -> str:
    """Kategoriya nomini identifikatorga o'xshash ko'rinishga soladi.

    CoinGecko javobida `id` ham, `name` ham bor va ular har doim
    bir xil yozilmaydi ("Layer 2 (L2)" -> "layer-2-l2"). Xarita
    identifikator bo'yicha yozilgan, lekin nom bo'yicha ham
    moslashish imkoni qolsin.
    """
    toza = [b.lower() if b.isalnum() else "-" for b in matn.strip()]
    natija = "".join(toza)
    while "--" in natija:
        natija = natija.replace("--", "-")
    return natija.strip("-")
