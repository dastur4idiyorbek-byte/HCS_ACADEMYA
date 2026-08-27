# Dizayn tizimi — ranglar logotipdan qanday olingan

## Qoida

Texnik topshiriqning 1-bo'limi ranglarni **taxmin qilishni taqiqlaydi**:
ular `public/logo.jpg` faylidan **piksel darajasida** o'qilishi kerak.
Shu sabab hech bir HEX kod "ko'zga chiroyli" degan asosda tanlanmagan.

Qayta tekshirish (Pillow kerak):

```bash
python3 scripts/logo_ranglari.py
```

Skript logotipdagi aniq koordinatalardan **9×9 kvadratning medianasini**
oladi — JPEG siqilishi bitta pikselni buzishi mumkin, mediana esa bunga
chidamli.

## O'lchangan ranglar

| Rang | HEX | Koordinata | Logotipdagi joyi |
|---|---|---|---|
| H turkuaz | `#01AAC1` | (210, 300) | "H" harfining chap ustuni |
| H turkuaz och | `#00BCD5` | (270, 318) | "H" ning ko'ndalang chizig'i |
| C apelsin | `#F47F16` | (420, 185) | "C" yoyining tepasi |
| S ko'k | `#10469C` | (440, 370) | "S" yoyining o'ng qismi |
| S ko'k to'q | `#133C7C` | (55, 590) | past-chap burchakdagi shakl |
| Sariq | `#F0B02A` | (600, 25) | tepa-o'ng burchakdagi shakl |
| Oq | `#F9F9F9` | (560, 120) | logotip foni |

## Rol taqsimoti (topshiriq qoidasi)

| Logotip harfi | Rol | O'zgaruvchi |
|---|---|---|
| **"S"** (to'q ko'k) | **FON** — sahifa va kartochkalar | `--rang-fon`, `--rang-panel` |
| **"C"** (apelsin) | **RAMKA** — har kartochka atrofidagi ingichka chiziq | `--rang-ramka` |
| **"H"** (turkuaz) | **MATN** — sarlavhalar, urg'u | `--rang-sarlavha` |

## Hisoblangan (o'lchanmagan) ranglar — 3 ta

Bu uchtasi logotipda **yo'q**, shuning uchun ular alohida belgilangan.
Har biri nima uchun kerakligi:

| O'zgaruvchi | HEX | Nima uchun hisoblangan |
|---|---|---|
| `--rang-fon` | `#0A2450` | Sahifa foni. `#133C7C` dan ~×0.62 qoraytirilgan. Kartochka logotipning **haqiqiy** ko'k rangida qolishi, lekin fondan ajralib turishi kerak — ikkalasi bir xil bo'lsa kartochka "suzib" ketadi. |
| `--rang-matn` | `#C7D4EA` | Uzun matn. Turkuaz uzun matnda ko'zni charchatadi, shuning uchun u faqat sarlavhaga qoldirilgan. Bu — logotip ko'kining och toni. |
| `--rang-matn-past` | `#9AB0D2` | `--rang-matn` ning xiraroq varianti — izoh, sana, manba ko'rsatkichlari uchun. |
| `--rang-past-toq` | `#E2402F` | Bozor Salomatligi shkalasining chap uchi. Topshiriq "to'yingan qizil" deydi, logotipda esa qizil yo'q — apelsin ohangiga moslangan. |
| `--rang-past` | `#F2695A` | Qizil **matn** va yorliq uchun. To'yingan qizil to'q ko'k fonda 2.6:1 beradi — o'qib bo'lmaydi, shuning uchun matn uchun ochroq toni ajratilgan. |

## Kontrast (WCAG)

Qorong'i interfeysda turkuaz matn o'qilmay qolishi mumkin — shuning uchun
har bir juftlik hisoblab chiqilgan:

Bu raqamlarni **qo'lda yozib qo'yish mumkin emas** — kimdir rangni bir oz
o'zgartirsa, hujjatdagi son o'z-o'zidan yolg'on bo'lib qoladi va buni hech
kim sezmaydi. Shuning uchun ular `globals.css` ning o'zidan o'qiladi:

```bash
python3 scripts/kontrast.py     # 0 — hammasi joyida, 1 — muammo bor
```

| Matn | Fon | Nisbat | Talab |
|---|---|---|---|
| `#00BCD5` sarlavha | `#133C7C` kartochka | 4.66 : 1 | 4.5 ✅ |
| `#C7D4EA` asosiy matn | `#133C7C` kartochka | 7.14 : 1 | 4.5 ✅ |
| `#9AB0D2` ikkinchi darajali | `#133C7C` kartochka | 4.84 : 1 | 4.5 ✅ |
| `#F47F16` ramka (chiziq) | `#133C7C` kartochka | 4.02 : 1 | 3.0 ✅ |
| `#00BCD5` yaxshi yorlig'i | `#0A2450` sahifa | 6.63 : 1 | 4.5 ✅ |
| `#F0B02A` o'rtacha yorlig'i | `#0A2450` sahifa | 7.93 : 1 | 4.5 ✅ |
| `#F2695A` past yorlig'i | `#0A2450` sahifa | 5.03 : 1 | 4.5 ✅ |

Aynan shu skript qurish paytida bitta xatoni tutdi: "🔴 Past" yorlig'i
to'yingan qizilda 2.55 : 1 bergan — ya'ni ko'rinardi-yu, o'qib
bo'lmasdi. Shundan keyin qizil ikkiga ajratildi (grafik / matn).

## O'lchamlar

- `--radius-kartochka: 14px` — topshiriq 12–16px oralig'ini so'ragan
- `--radius-tugma: 12px`, `--radius-kichik: 10px`
- Har bir kartochka **1px ramka** bilan o'ralgan. Oddiy kartochkada ramka
  apelsinning 62% shaffofligida: ekranda o'nlab kartochka bo'lsa,
  hammasi to'liq apelsin bo'lib turishi ko'zni charchatadi va urg'u
  urg'u bo'lib qolmaydi. `variant="urgu"` — to'liq apelsin.

## Shrift

`Inter`, `subsets: ["latin", "latin-ext", "cyrillic"]`. Kirill **ataylab**
qo'shilgan: sayt o'zbek va rus tillarida ishlaydi (topshiriq 8-bo'limi).
Shrift kirillni qo'llab-quvvatlamasa, rus tilidagi matn brauzerning
zaxira shriftiga tushib, sahifa ikki xil ko'rinadi.
