/** Akademiya — sof hisob-kitob (tarmoqsiz, bazasiz).
 *
 * `queries.ts` bazadan o'qiydi, bu yerda esa faqat shakl beriladi:
 * vaqtni matnga aylantirish, ilgarilashni birlashtirish. Shu sababli
 * test yozish oson va u brauzerda ham ishlaydi.
 */

/** Soniyani "12:45" ko'rinishiga keltiradi.
 *
 * `null` uchun bo'sh satr — chiziqcha ham, "0:00" ham emas. Nol
 * uzunlik "video 0 soniya" degan MA'LUMOT bo'lardi; aslida biz
 * uzunlikni bilmaymiz va bu holda hech narsa yozilmaydi.
 */
export function davomiylikMatn(soniya: number | null): string {
  if (soniya === null || !Number.isFinite(soniya) || soniya <= 0) return "";
  const soat = Math.floor(soniya / 3600);
  const daqiqa = Math.floor((soniya % 3600) / 60);
  const qolgan = Math.floor(soniya % 60);
  const ikki = (n: number) => String(n).padStart(2, "0");
  return soat > 0
    ? `${soat}:${ikki(daqiqa)}:${ikki(qolgan)}`
    : `${daqiqa}:${ikki(qolgan)}`;
}

/** Maqolani o'qish vaqti — "3 daq".
 *
 * Uzunlik yozilmagan bo'lsa bo'sh qaytadi: taxminiy raqam
 * ko'rsatishdan ko'ra hech narsa demaslik rost.
 */
export function oqishVaqti(soniya: number | null, qisqartma: string): string {
  if (soniya === null || soniya <= 0) return "";
  return `${Math.max(1, Math.round(soniya / 60))} ${qisqartma}`;
}
