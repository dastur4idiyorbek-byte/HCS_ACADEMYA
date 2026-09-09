import { redirect } from "next/navigation";

/** Eski manzil — Bozor holati sahifasiga yo'naltiradi.
 *
 * NEGA FAYL O'CHIRILMADI. Bozor Salomatligi bir necha oy alohida
 * sahifa bo'lib turdi: uning havolasi Telegramdagi xabarlarda,
 * foydalanuvchilarning xatcho'plarida va tashqi joylarda qolgan
 * bo'lishi mumkin. Fayl o'chirilsa, o'sha havolalar 404 beradi va
 * odam saytda xato bor deb o'ylaydi.
 *
 * Mazmuni endi `/bozor-holati` ichida — sahifaning eng tepasida.
 */
export default function Salomatlik() {
  redirect("/bozor-holati");
}
