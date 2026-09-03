import { db, vaqt } from "./db.ts";

/** Sayt uchun bozor ko'rinishi — haftalik va kunlik post.
 *
 * LOYIHA EGASINING SHARTI: bu SIGNALGA BOG'LANMAYDI. Asosiy tahlil 4
 * soatlikda qoladi; haftalik va kunlik — faqat shu sahifa uchun.
 *
 * NIMA UCHUN SAYT HISOBLAMAYDI. Postni bot quradi: unda BTC va ETH
 * shamlari bor, saytda esa yo'q. Ikki joyda hisoblansa, ikkita javob
 * paydo bo'lardi — bu loyihada bir necha marta uchragan xato turi
 * (`docs/ARXITEKTURA.md`, 68-bo'lim). Sayt faqat O'QIYDI.
 *
 * Alohida fayl: `queries.ts` allaqachon juda katta va yangi bo'limni
 * unga qo'shish uni yana o'stirardi.
 */

export type Yonalish = "up" | "down" | "flat";

export type BozorAsbobi = {
  kod: string;
  nom: string;
  qiymat: number;
  ozgarish: number | null;
  yonalish: Yonalish;
  ulush: boolean;
  izoh: string;
};

export type BozorPosti = {
  turi: "haftalik" | "kunlik";
  sana: Date | null;
  asboblar: BozorAsbobi[];
  xulosa: string;
  kutilma: string;
};

type Qator = {
  turi: string;
  sana: string;
  asboblar_json: string;
  xulosa: string;
  kutilma: string;
};

function tahlil(qator: Qator | undefined): BozorPosti | null {
  if (!qator) return null;

  let asboblar: BozorAsbobi[] = [];
  try {
    asboblar = JSON.parse(qator.asboblar_json) as BozorAsbobi[];
  } catch {
    // Buzuq JSON butun sahifani yiqitmasin — qatorsiz ko'rsatiladi.
    asboblar = [];
  }

  return {
    turi: qator.turi === "haftalik" ? "haftalik" : "kunlik",
    sana: vaqt(qator.sana),
    asboblar,
    xulosa: qator.xulosa,
    kutilma: qator.kutilma,
  };
}

/** Shu turdagi ENG SO'NGGI post. */
export function bozorPosti(turi: "haftalik" | "kunlik"): BozorPosti | null {
  const qator = db()
    .prepare(
      `SELECT turi, sana, asboblar_json, xulosa, kutilma
         FROM bozor_korinishlari
        WHERE turi = ?
        ORDER BY sana DESC
        LIMIT 1`,
    )
    .get(turi) as Qator | undefined;
  return tahlil(qator);
}
