/** Shartli class nomlarini birlashtiradi.
 *
 * Nima uchun kutubxona emas: bizga faqat "bo'sh qiymatlarni tashlab,
 * qolganini bo'sh joy bilan qo'shish" kerak. `clsx` + `tailwind-merge`
 * juftligi shu bitta ish uchun ortiqcha bog'liqlik bo'lardi.
 */
export type ClassValue = string | false | null | undefined;

export function cn(...qismlar: ClassValue[]): string {
  return qismlar.filter(Boolean).join(" ");
}
