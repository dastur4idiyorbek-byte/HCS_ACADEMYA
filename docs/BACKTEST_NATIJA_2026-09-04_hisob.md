# 1000$ hisob natijasi — signal YAXSHI, PUL BOSHQARUVI BUZUQ

Sana: 2026-09-04 | Actions: 33839399520 | 12 halol coin, 4 yil

## Ikki raqam qarama-qarshi

    Savdolarning o'zi:   498 savdo, PF 3.49, 68% foydali
    1000$ hisobda:       $1000 -> $319   (-68.1%)

## Sabab TOPILDI va o'lchandi

389 signaldan hisob faqat **131 tasini** oldi. 258 tasi kapital
band bo'lgani uchun o'tkazib yuborildi. Tanlov TASODIFIY emas:

| | O'rtacha natija |
|---|---|
| Hisob OLGAN savdolar | **−3.44%** |
| Hisob O'TKAZIB YUBORGAN savdolar | **+6.04%** |
| Farq | **9.48%** |

### Mexanizm

Zararli savdo TEZ yopiladi — stop tegadi, kapital bo'shaydi.
Foydali savdo UZOQ yuradi — TP2/TP3 gacha 28 kungacha, kapital
band turadi.

Natijada hisob har safar **zarardan keyin** bo'shagan pulga
yangi signal oladi, foyda ketayotgan paytda esa yangi signalni
**o'tkazib yuboradi**. Ya'ni tizim o'zi yutqazadigan savdolarni
tanlab oladi.

Bu — kodning xatosi EMAS. Bu — `sequential_decay` + uzun
ushlash + kapital cheklovi uchligining tuzilmaviy oqibati.

### Simulyator tekshirildi

Xulosa chiqarishdan oldin simulyatorning o'ziga shubha
qilindi. Sun'iy oqimda (musbat PF) u +1343% berdi; kapital
bosimi oshirilganda ham musbat qoldi. Ya'ni simulyator
ishlayapti — muammo haqiqiy oqimda.

## 🔴 XULOSA

**Signal sifati va pul boshqaruvi — IKKI BOSHQA narsa.**
Birinchisi o'lchov bo'yicha yaxshi, ikkinchisi buzuq.

Modul jonliga chiqmaydi. Lekin sabab endi ma'lum va u
tahlil modulida emas — `core/position_sizing` da.

## 🔴 O'LCHANMAGAN — keyingi qadam

Quyidagilar MANTIQAN yechim bo'lishi mumkin, lekin
O'LCHANMAGAN, shuning uchun taxmin sifatida yoziladi:

| 🔴 | Gipoteza |
|---|---|
| 🔴 | Har savdoga TENG ulush (decay o'rniga) |
| 🔴 | Ochiq savdolar soniga qarab kapitalni oldindan bo'lish |
| 🔴 | Uzoq ushlanadigan savdoga kamroq kapital |
| 🔴 | Kapital yetmasa — signalni KUTISH, tashlamaslik |

Hech biri backtestsiz qo'llanmaydi.
