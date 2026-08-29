/** QT — Quarterly Theory (AMDX) davri.
 *
 * MANBA: `core/analysis/market_health/quarterly.py`. Bu yerda IKKINCHI
 * NUSXA bor, chunki sahifa davrni ko'rsatishi kerak, lekin baza faqat
 * davrning BALLINI saqlaydi — nomini emas.
 *
 * Ikki nusxa xavfli, shuning uchun u ochiq boshqariladi:
 *   1. Qoida juda sodda va o'zgarmas — sutka to'rtta olti soatlik
 *      chorakka bo'linadi, boshqa hech qanday parametr yo'q;
 *   2. `tests/davr.test.ts` chegaralarni qulflaydi. Python tomonda
 *      `tests/core/test_score_bonuses.py` aynan shu chegaralarni
 *      tekshiradi — biri o'zgarsa, ikkinchisi yiqiladi.
 *
 * OCHIQ CHEKLOV: davr SOAT bo'yicha aniqlanadi, ya'ni u bozor
 * holatidan qat'i nazar har kuni bir xil ritmda o'zgaradi. Shuning
 * uchun uning indeksdagi vazni ataylab kichik (5) va qiymatlar
 * backtest bilan tasdiqlanishi kerak.
 */

export type Davr = "A" | "M" | "D" | "X";

/** Sutka nechta chorakka bo'linadi (AMDX -> to'rtta) */
export const CHORAKLAR = 4;
const SOAT_CHORAKDA = 24 / CHORAKLAR;

const TARTIB: Davr[] = ["A", "M", "D", "X"];

/** Berilgan UTC vaqti sutkaning qaysi choragida. */
export function davr(vaqt: Date): Davr {
  const soat = vaqt.getUTCHours();
  return TARTIB[Math.min(CHORAKLAR - 1, Math.floor(soat / SOAT_CHORAKDA))];
}

/** Keyingi davr — "hozir qayerdamiz, keyin nima" degan savol uchun. */
export function keyingiDavr(joriy: Davr): Davr {
  return TARTIB[(TARTIB.indexOf(joriy) + 1) % CHORAKLAR];
}
