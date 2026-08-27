/** Hozirgi vaqt — ATAYLAB `async`.
 *
 * Server komponentida `new Date()` ni to'g'ridan-to'g'ri chaqirish
 * "render paytida sof bo'lmagan funksiya" hisoblanadi: React render'ni
 * qayta ishga tushirishi mumkin va har safar boshqa qiymat chiqadi.
 * `await` orqali olsak, qiymat render boshlanishidan oldin bir marta
 * hisoblanadi va sahifa ichida o'zgarmaydi.
 */
export async function hozir(): Promise<Date> {
  return new Date();
}
