/** Jonli Oshxona monitori — bosqich kodini NOM KALITIGA aylantirish.
 *
 * Bazadagi kod strategiya prefiksi bilan keladi
 * (`classic_ta:zone_position`), ba'zan esa undan ham aniqroq
 * (`classic_ta:levels:stop_too_close`). Ekranda esa bosqichning
 * NEYTRAL nomi kerak.
 *
 * NIMA UCHUN `stage_label()` EMAS: Python tomonidagi `STAGE_LABELS`
 * — RAD ETISH SABABLARI ("Halol ro'yxatda emas"). Ular voronkada
 * to'g'ri, monitorda esa yolg'on bo'lardi: o'tgan bosqich yonida
 * "✅ Halol ro'yxatda emas" degan yozuv chiqardi.
 *
 * Sof funksiya — mijoz tomonda ham ishlaydi (`node:fs` ga bog'liq
 * `bosqichlar.ts` dan farqli).
 */
export function bosqichKaliti(kod: string): string {
  const qismlar = kod.split(":");
  if (qismlar.length === 1) return qismlar[0];
  // Risk Engine ning 13 ta qoidasi bitta bosqich sifatida ko'rinadi:
  // qaysi qoida to'xtatgani SABAB qatorida yoziladi.
  if (qismlar[0] === "risk_engine") return "risk_engine";
  return qismlar[1];
}
