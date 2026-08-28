import { sozlama } from "./config.ts";

/** Pozitsiya hajmi tavsiyasi — BOTDAGI hisobning aynan o'zi.
 *
 * NEGA IKKINCHI NUSXA BOR: asl hisob `core/position_sizing/` da,
 * Pythonda. Sayt esa TypeScriptda ishlaydi va bu raqamni saytda ham
 * ko'rsatishi kerak — kalkulyatorning boshlang'ich summasi va "Men
 * sotib oldim" dagi taklif shundan keladi.
 *
 * IKKI NUSXA — XAVF, shuning uchun u ochiq boshqariladi:
 *
 *   1. Barcha parametrlar `config/default.yaml` dan o'qiladi, ya'ni
 *      ikkalasi BIR XIL sozlamaga qaraydi;
 *   2. `tests/position_sizing/fixtures.json` — Python hisoblab
 *      chiqargan qiymatlar. Python testi ham, saytdagi test ham SHU
 *      faylga solishtiradi. Biror tomon o'zgarsa, testlardan biri
 *      darhol yiqiladi.
 *
 * FAQAT KO'RSATISH YO'LI ko'chirilgan (`commit=False`): kunlik
 * byudjetdan xavf AJRATISH Pythonda qoladi. Bot kartochka yasashda
 * har safar yangi byudjet ochadi (`budget_for`), ya'ni bu yo'lda
 * `allocated` va `committed_capital` doim nol — natija esa faqat
 * balans va Stop masofasiga bog'liq.
 */

export type Taklif = {
  /** Kunlik xavf foizi — balans pog'onasidan */
  kunlikXavfFoiz: number;
  /** Kunlik xavf byudjeti, dollarda */
  kunlikByudjet: number;
  /** Shu signalga tavsiya etilgan pozitsiya hajmi, dollarda */
  hajm: number;
  /** Shu pozitsiyada xavf ostidagi pul */
  xavf: number;
  /** Hajm kapital chegarasi bilan KESILGANMI (spot: leverage yo'q) */
  kesilgan: boolean;
};

type Pogona = { max_balance: number | null; daily_risk_pct: number };

/** Balans pog'onasiga mos kunlik xavf foizi (5.1-band). */
export function kunlikXavfFoizi(balans: number): number {
  const pogonalar = sozlama<Pogona[]>(["position_sizing", "risk_tiers"], []);
  if (pogonalar.length === 0) {
    throw new Error("position_sizing.risk_tiers sozlanmagan");
  }
  for (const p of pogonalar) {
    if (p.max_balance === null || p.max_balance === undefined) return p.daily_risk_pct;
    if (balans <= p.max_balance) return p.daily_risk_pct;
  }
  return pogonalar[pogonalar.length - 1].daily_risk_pct;
}

/** Bitta signal uchun hajm tavsiyasi. `null` — hisoblab bo'lmadi. */
export function hajmTaklifi(balans: number, entry: number, stop: number): Taklif | null {
  if (!(balans > 0) || !(entry > 0) || !(stop > 0) || stop >= entry) return null;

  const stopFoiz = ((entry - stop) / entry) * 100;
  if (stopFoiz <= 0) return null;

  const usul = sozlama<string>(["position_sizing", "allocation_method"], "sequential_decay");
  const ulush = sozlama<number>(["position_sizing", "sequential_decay_fraction"], 0.34);
  const joylar = sozlama<number>(["position_sizing", "equal_split_expected_slots"], 3);
  const engKam = sozlama<number>(["position_sizing", "min_allocation_usd"], 1);
  const engKattaFoiz = sozlama<number>(
    ["position_sizing", "max_position_pct_of_balance"],
    100,
  );

  const foiz = kunlikXavfFoizi(balans);
  const byudjet = (balans * foiz) / 100;

  // Yangi byudjet: `allocated` va `committed_capital` nol, ya'ni
  // "qolgan" = butun byudjet, "bo'sh kapital" = butun balans.
  const bolish = (mavjud: number) =>
    usul === "equal_split" ? mavjud / Math.max(1, joylar) : mavjud * ulush;

  let rejaXavf = Math.min(bolish(byudjet), byudjet);
  if (rejaXavf < engKam) rejaXavf = 0;
  if (rejaXavf <= 0) {
    return { kunlikXavfFoiz: foiz, kunlikByudjet: byudjet, hajm: 0, xavf: 0, kesilgan: false };
  }

  const xomHajm = rejaXavf / (stopFoiz / 100);
  // Uch bosqichli cheklov — spot savdoda leverage yo'q.
  const engKattaHajm = Math.min(
    (balans * engKattaFoiz) / 100,
    balans,
    Math.min(bolish(balans), balans),
  );
  const hajm = Math.min(xomHajm, engKattaHajm);
  if (hajm <= 0) {
    return { kunlikXavfFoiz: foiz, kunlikByudjet: byudjet, hajm: 0, xavf: 0, kesilgan: false };
  }

  return {
    kunlikXavfFoiz: foiz,
    kunlikByudjet: byudjet,
    hajm,
    xavf: Math.min(rejaXavf, (hajm * stopFoiz) / 100),
    kesilgan: hajm < xomHajm,
  };
}
