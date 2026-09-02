/** QT — Quarterly Theory (AMDX) davri.
 *
 * DAVR ENDI SOATDAN HISOBLANMAYDI. Ilgari bu yerda sutkani to'rt
 * chorakka bo'ladigan nusxa turardi va u bozor holatidan qat'i nazar
 * har kuni bir xil ritmda o'zgarardi. Endi davr NARX HARAKATIDAN
 * o'qiladi (`core/analysis/market_health/quarterly.py`) va bazaga
 * HARF sifatida yoziladi.
 *
 * Ya'ni ikkinchi nusxa YO'Q bo'ldi: sayt hisoblamaydi, o'qiydi.
 * Bu yerda faqat KO'RSATISH yordamchilari qoldi.
 */

export type Davr = "A" | "M" | "D" | "X";

/** AMDX tartibi — "hozir qayerdamiz, keyin nima" uchun */
export const TARTIB: Davr[] = ["A", "M", "D", "X"];

export function davrmi(x: unknown): x is Davr {
  return x === "A" || x === "M" || x === "D" || x === "X";
}

/** Keyingi davr — aylanma tartibda. */
export function keyingiDavr(joriy: Davr): Davr {
  return TARTIB[(TARTIB.indexOf(joriy) + 1) % TARTIB.length];
}
