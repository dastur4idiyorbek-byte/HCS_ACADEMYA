# HALOL CRYPTO SAVDO — veb-sayt

Telegram botning **qo'shimcha interfeysi**. Botni almashtirmaydi:
`core/` (miya) o'zgarishsiz qoladi, sayt esa bazani o'qiydi va pullik
amallar uchun foydalanuvchini botga yo'naltiradi.

## Muhit o'zgaruvchilari

Sayt bot bilan BIR XIL o'zgaruvchilarni ishlatadi (`.env.example` ga
qarang) — alohida nusxa saqlanmaydi:

| O'zgaruvchi | Nima uchun |
|---|---|
| `BOT_TOKEN` | Telegram kirishini tekshirish (HMAC) va sessiya imzosi. **Majburiy.** |
| `BOT_USERNAME` | Login Widget uchun bot nomi, `@` siz. **Majburiy.** |
| `ADMIN_IDS` | Kim admin — botdagi bilan bir xil manba |
| `DATABASE_URL` | Bot bazasiga yo'l (SQLite) |
| `HCS_CONFIG_FILE` | Ixtiyoriy. Nisbiy bo'lsa loyiha ILDIZIGA nisbatan hisoblanadi |

Mahalliy ishlash uchun `web/.env.local` yarating.

## Ishga tushirish

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

Bo'sh bazada sahifalarni ko'rish uchun namunaviy ma'lumot:

```bash
node scripts/demo_malumot.mjs    # faqat baza bo'sh bo'lganda ishlaydi
```

## Joylashtirish

Sayt **Railway'da, bot bilan bitta xizmatda** ishlaydi
(`scripts/start.sh`, `nixpacks.toml`, `railway.toml`).

Nima uchun Vercel emas: Railway'da doimiy disk faqat bitta xizmatga
ulanadi, baza esa o'sha diskdagi SQLite fayli. Sayt uni to'g'ridan-to'g'ri
o'qiydi — demak ikkalasi bir konteynerda yashashi shart. Vercel'ga
o'tish uchun avval baza PostgreSQL'ga ko'chirilishi kerak; o'sha paytda
faqat `src/lib/db.ts` va `src/lib/queries.ts` qayta yoziladi, qolgan
qatlamlar tegilmaydi.

**Telegram sozlamasi:** BotFather'da `/setdomain` orqali saytning
domenini botga bog'lang — ansiz Login Widget umuman chiqmaydi.

## Tekshiruvlar

```bash
npx tsc --noEmit             # tiplar
npx eslint .                 # lint
npm run build                # ishlab chiqarish uchun yig'ish
npm test                     # birlik testlari (node --test)
python3 scripts/kontrast.py  # WCAG kontrast (globals.css dan o'qiydi)
python3 scripts/logo_ranglari.py   # ranglar logotipga mos ekanini tekshirish
```

## Tuzilma

```
src/app/          — sahifalar (App Router)
src/components/ui — dizayn tizimi (Card, Button, Badge, Logo)
src/lib/          — yordamchi funksiyalar
public/logo.jpg   — LOGOTIP: barcha ranglar shu fayldan o'lchangan
scripts/          — ranglar va kontrast tekshiruvi (build qismi emas)
```

Ranglar qanday olingani va nima uchun aynan shunday ekani —
[`DIZAYN.md`](./DIZAYN.md).

## Signal himoyasi

Vebda `protect_content` ning ekvivalenti **yo'q** — skrinshotni to'liq
to'sib bo'lmaydi. `components/Himoya.tsx` uchta qatlam beradi: fokus
yo'qolganda narxlar xiralashadi, ustida foydalanuvchining Telegram IDsi
suv belgisi bo'lib turadi, nusxalash va chop etish bloklangan. Batafsil:
`docs/ARXITEKTURA.md`, 50-bo'lim.

## Holati

| Bosqich | Holat |
|---|---|
| 1. Skelet + dizayn tizimi | ✅ |
| 2. Telegram Login + HMAC | ✅ |
| 3. Layout, 8 bo'lim | ✅ |
| 4. Bozor Salomatligi shkalasi | ✅ |
| 5. Signallar / Statistika / Portfel | ✅ |
| 6. "Nega signal yo'q?" voronkasi | ✅ |
| 7. Video darsliklar / Onlayn kurs | ✅ |
| 8. Profil / Obuna | ✅ |
| 9. Admin panel | ✅ |
| 10. Responsive tekshiruv | ✅ |
| 11. Joylashtirish sozlamasi (Railway) | ✅ |
