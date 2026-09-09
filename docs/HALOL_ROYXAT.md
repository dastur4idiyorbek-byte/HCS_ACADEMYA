# Kuzatiladigan coinlar — halol ro'yxat

Bu fayl **yagona manba**. `core/config/schema.py` dagi
`kuzatiladigan_coinlar` shu ro'yxat bilan bir xil bo'lishi shart va
`tests/core/test_zanjir_sikl.py` buni mexanik tekshiradi.

Nima uchun alohida hujjat: ro'yxatning o'zi kodda turadi, lekin
**nima uchun aynan shu coinlar** degan savolning javobi kodda
turmaydi. Ikkalasi ajralib qolsa, bir kun kelib hech kim nima
uchun falon coin ro'yxatda ekanini ayta olmaydi.

---

## Holat: TASDIQ KUTILMOQDA

⚠️ **Bu ro'yxat diniy hujjat emas.** U tijorat skrining xizmatining
natijasidan olingan va bilimli kishi tomonidan tasdiqlanmagan.
Tasdiq kelguncha ro'yxat "ishchi taxmin" maqomida qoladi.

| | |
|---|---|
| **Manba** | SharifBot — `sharifbot.com/pages/halal-coins` |
| **Mezon** | AAOIFI Shariah Standard 17 |
| **Manba sanasi** | 2026-iyul (saytda "Last reviewed July 2026") |
| **Olingan sana** | 2026-09-09 |
| **Tasdiqlagan olim** | ❌ yo'q — kutilmoqda |

---

## Qanday tanlandi

Avvalgi ro'yxatda **200 ta** coin bor edi. U bozor kapitali bo'yicha
tuzilgan va **hech kim uni halollikka tekshirmagan** — loyihaning
halol testi atigi ~30 ta urug' nomni bilardi, qolgan ~170 tasi
jimgina o'tib ketardi.

SharifBot ro'yxatida 143 ta coin bor. Ikkisi kesishtirildi:

    Bizning ro'yxat        200 ta
    SharifBot halol        143 ta
    ------------------------------
    Ikkalasida ham bor      80 ta   <- shu ro'yxat
    Faqat bizda            120 ta   <- CHIQARILDI
    Faqat SharifBot'da      63 ta   <- QO'SHILMADI

**Chiqarilgan 120 ta.** Ular tasodifan tushib qolmagan. Ba'zilarining
sababi ochiq ko'rinib turadi:

| Coin | Nima qiladi |
|---|---|
| ONDO | AQSH obligatsiyalarini tokenlashtiradi — **foiz** |
| ALPACA | **Leverage** bilan yield farming |
| XVS, KAVA, ACA | qarz berish/olish platformalari — **riba** |
| PERP | perpetual (fyuchers) |
| FUN | FunFair — **qimor** |
| 1INCH, SUSHI, YFI, BAL, DODO | DeFi, foizli mahsulotlar bilan bog'liq |
| EIGEN, ETHFI, JTO | restaking va daromad mahsulotlari |
| UNI, JUP, RAY | DEX; JUP'da perpetual savdo ham bor |

Bular loyihaning eng asosiy va'dalariga — riba yo'q, leverage yo'q,
qimor yo'q — bevosita tegadi.

**Qo'shilmagan 63 ta.** SharifBot ularni halol deydi, lekin ko'pi juda
yangi va kam savdoli (`2Z`, `BREV`, `MIRA`, `SAPIEN`, `TOWNS`). Kam
likvidlik modul uchun alohida xavf va u hech qachon o'lchanmagan.
Ular keyin, likvidlik chegarasi o'lchangandan so'ng ko'riladi.

**Tasdiqlanmagan ≠ harom.** SharifBot ro'yxatida yo'qligi coin harom
degani emas — u shunchaki tekshirilmagan ham bo'lishi mumkin. Lekin
biz uchun natija bir xil: tasdiqlanmagan coin ro'yxatga kirmaydi.
Bu CrypoIslam kanalining o'z qoidasi bilan ham mos —
*"shubhali coin bilan savdo qilinmaydi, xuddi harom kabi"*.

---

## O'LCHANMAGAN

Tizimning o'lchovi **12 ta coinda** o'tkazilgan (4 yil, 498 savdo,
PF 3.49). Bu 80 ta — boshqa to'plam. **80 coinda tizim qanday
ishlashi hech qachon o'lchanmagan.**

O'lchangan 12 tasi shu 80 talikning ichida:
BTC, ETH, SOL, ADA, AVAX, LINK, DOT, BCH, LTC, NEAR, ETC, FIL.

Batafsil: `docs/GIPOTEZA_DAFTARI.md`.

---

## Ro'yxat (80 ta)

BTC ETH SOL ADA AVAX LINK DOT BCH LTC NEAR
ETC FIL APT SUI POL XLM HBAR VET ATOM OP
ARB TAO TIA STX IMX GRT RENDER ALGO EGLD THETA
S PYTH FLOW MINA AR CKB ZIL ONE KSM CELO
BAT IOTA XTZ QTUM NEO STORJ SC RVN MASK API3
TRB ICX ONT ASTR MOVR STRAX PHA REQ BICO RARE
JASMY STRK XEC TFUEL HOT IOST STEEM HIVE ACH RIF
CTSI EDU DYM SAGA TWT CHR AVA CVC QKC DGB

---

## Keyingi qadamlar

1. CrypoIslam kanali (`t.me/CrypoIslam`) bilan solishtirish — ikkala
   manba rozi bo'lganlarni ajratish
2. Ro'yxatni bilimli kishiga ko'rsatish va tasdiq olish
3. 80 coinda backtest o'tkazish
4. Likvidlik chegarasi o'lchangach, 63 talikni qayta ko'rish

Hukm o'zgarishi mumkin: manba kartalarida ochiq yozilgan —
*"har qanday coinning hukmi istalgan vaqtda o'zgarishi mumkin"*.
Shuning uchun ro'yxat vaqti-vaqti bilan qayta tekshiriladi.
