/** Portfel dashboardi — BOTDAGI hisobning aynan o'zi.
 *
 * NEGA IKKINCHI NUSXA BOR: asl hisob `core/portfolio/` da, Pythonda.
 * Sayt esa TypeScriptda ishlaydi va o'sha raqamni ko'rsatishi kerak.
 *
 * IKKI NUSXA — XAVF, shuning uchun u ochiq boshqariladi:
 *
 *   `tests/portfel_fixtures.json` — Python hisoblab chiqargan
 *   qiymatlar. Python testi (`tests/test_portfel_fixtures.py`) ham,
 *   saytdagi test (`web/tests/portfel.test.ts`) ham SHU faylga
 *   solishtiradi. Biror tomon o'zgarsa, testlardan biri darhol
 *   yiqiladi.
 *
 * 3-promptning "BITTA MANBA, IKKI EKRAN" talabi shu tarzda
 * bajariladi: bir xillikni izoh emas, test ushlab turadi.
 */

/** Davr kaliti -> foydalanuvchi ko'radigan nom.
 *  `core/portfolio/pnl_dashboard.py: DAVR_NOMLARI` bilan bir xil. */
export const DAVR_NOMLARI: Record<string, string> = {
  bugun: "Bugungi",
  hafta: "7 kunlik",
  oy: "30 kunlik",
  boshidan: "Boshidan beri",
};

/** Davr -> necha kun (null = boshidan beri).
 *  `core/portfolio/pnl_calculator.py: DAVRLAR` bilan bir xil. */
export const DAVRLAR: [string, number | null][] = [
  ["bugun", 1],
  ["hafta", 7],
  ["oy", 30],
  ["boshidan", null],
];

/** Shundan kichik pozitsiya ochilmaydi — bo'lak "band" sanaladi.
 *  `core/portfolio/capital_allocator.py: ENG_KAM_MIQDOR_USD`. */
export const ENG_KAM_MIQDOR_USD = 5.0;

export type YopilganQism = {
  signalId: number;
  /** Yopilgan vaqt — UTC */
  yopilganVaqt: Date;
  natijaUsd: number;
};

export type OchiqPozitsiya = {
  signalId: number;
  /** Coin — joriy narxni izlash uchun. Hisobda ISHLATILMAYDI,
   *  shuning uchun etalon faylda ham yo'q. */
  symbol?: string;
  entry: number;
  ochiqMiqdorUsd: number;
  /** Joriy narx, yoki null — narx OLINMADI (birja javob bermadi) */
  joriyNarx: number | null;
};

export type Bolak = {
  raqam: number;
  hajm: number;
  bandKapital: number;
  bandXavf: number;
};

export type DashboardQatori = { nom: string; usd: number; pct: number };

export type Dashboard = {
  qatorlar: DashboardQatori[];
  unrealizedUsd: number;
  ochiqSoni: number;
  /** Joriy narxi olinmagan ochiq savdolar — unrealized ga KIRMAGAN */
  baholanmaganSoni: number;
  bandBolaklar: number[];
  boshBolaklar: number[];
  xavfPct: number;
  /** Hech qanday savdo bo'lmaganmi — ekran raqam emas, rostini aytadi */
  bosh: boolean;
};

/** "Bugun" — KALENDAR kun boshi, oxirgi 24 soat emas.
 *
 * Kecha kechqurun yopilgan savdo "bugungi" natijaga tushmasligi kerak:
 * foydalanuvchi ertalab ochib, tushunarsiz raqam ko'rardi. */
function kesim(hozir: Date, kun: number | null): Date | null {
  if (kun === null) return null;
  if (kun === 1) {
    return new Date(
      Date.UTC(hozir.getUTCFullYear(), hozir.getUTCMonth(), hozir.getUTCDate()),
    );
  }
  return new Date(hozir.getTime() - kun * 24 * 60 * 60 * 1000);
}

function unrealized(p: OchiqPozitsiya): number {
  if (p.joriyNarx === null || p.entry <= 0) return 0;
  return (p.ochiqMiqdorUsd * (p.joriyNarx - p.entry)) / p.entry;
}

function baholandimi(p: OchiqPozitsiya): boolean {
  return p.joriyNarx !== null && p.entry > 0;
}

/** Bo'lakda yangi pozitsiya uchun joy qoldimi. */
export function bolakBand(b: Bolak): boolean {
  return Math.max(0, b.hajm - b.bandKapital) < ENG_KAM_MIQDOR_USD;
}

/** Butun balansning necha foizi hozir xavf ostida. */
export function umumiyXavfPct(bolaklar: Bolak[]): number {
  const jamiHajm = bolaklar.reduce((s, b) => s + b.hajm, 0);
  if (jamiHajm <= 0) return 0;
  return (bolaklar.reduce((s, b) => s + b.bandXavf, 0) / jamiHajm) * 100;
}

/** PNL va kapital holatidan bitta manzara yasaydi.
 *
 * Realized va unrealized ARALASHTIRILMAYDI — 3-promptning qat'iy
 * talabi. Ochiq savdoning "foydasi" hali pul emas. */
export function dashboardQur(
  qismlar: YopilganQism[],
  ochiqlar: OchiqPozitsiya[],
  bolaklar: Bolak[],
  balansUsd: number,
  hozir: Date = new Date(),
): Dashboard {
  const qatorlar: DashboardQatori[] = [];
  let savdoBormi = false;

  for (const [nom, kun] of DAVRLAR) {
    const chegara = kesim(hozir, kun);
    const tanlangan = qismlar.filter(
      (q) => chegara === null || q.yopilganVaqt.getTime() >= chegara.getTime(),
    );
    const jami = tanlangan.reduce((s, q) => s + q.natijaUsd, 0);
    if (nom === "boshidan" && tanlangan.length > 0) savdoBormi = true;
    qatorlar.push({
      nom: DAVR_NOMLARI[nom] ?? nom,
      usd: jami,
      pct: balansUsd > 0 ? (jami / balansUsd) * 100 : 0,
    });
  }

  return {
    qatorlar,
    unrealizedUsd: ochiqlar.reduce((s, p) => s + unrealized(p), 0),
    ochiqSoni: ochiqlar.length,
    baholanmaganSoni: ochiqlar.filter((p) => !baholandimi(p)).length,
    bandBolaklar: bolaklar.filter(bolakBand).map((b) => b.raqam),
    boshBolaklar: bolaklar.filter((b) => !bolakBand(b)).map((b) => b.raqam),
    xavfPct: umumiyXavfPct(bolaklar),
    bosh: !savdoBormi && ochiqlar.length === 0,
  };
}
