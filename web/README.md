# HALOL CRYPTO SAVDO — veb-sayt

Telegram botning **qo'shimcha interfeysi**. Botni almashtirmaydi:
`core/` (miya) o'zgarishsiz qoladi, sayt esa bazani o'qiydi va pullik
amallar uchun foydalanuvchini botga yo'naltiradi.

## Ishga tushirish

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

## Tekshiruvlar

```bash
npx tsc --noEmit             # tiplar
npx eslint .                 # lint
npm run build                # ishlab chiqarish uchun yig'ish
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

## Holati

| Bosqich | Holat |
|---|---|
| 1. Skelet + dizayn tizimi | ✅ |
| 2. Telegram Login + HMAC | ⏳ |
| 3. Layout, 8 bo'lim | ⏳ |
| 4. Bozor Salomatligi shkalasi | ⏳ |
| 5. Signallar / Statistika / Portfel | ⏳ |
| 6. "Nega signal yo'q?" voronkasi | ⏳ |
| 7. Video darsliklar / Onlayn kurs | ⏳ |
| 8. Profil / Obuna | ⏳ |
| 9. Admin panel | ⏳ |
| 10. Responsive tekshiruv | ⏳ |
| 11. Vercel sozlamasi | ⏳ |
