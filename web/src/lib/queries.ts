import { db, songaAylantir, vaqt, vaqtSatri } from "./db.ts";
import {
  engKichikPozitsiya,
  kotirovka,
  obunaKunlari,
  savdoQoidalari,
} from "./config.ts";
import { asosiyAktiv } from "./kalkulyator.ts";

/** Botning bazasidan o'qish/yozish.
 *
 * Qoida: bu yerda BIZNES MANTIQ yozilmaydi. Ball hisoblash, Risk Engine,
 * Bozor Salomatligi — hammasi `core/` da qoladi va o'zgarmaydi (topshiriq
 * "MUHIM KO'RSATMA" bandi). Sayt faqat natijani ko'rsatadi.
 *
 * Yagona istisno — to'lovni tasdiqlash: u BAZAGA YOZADI, chunki admin
 * paneli saytda ham bo'lishi kerak (7-bo'lim). Bu yozuv botdagi
 * `SubscriptionService.approve_payment` bilan bir xil qadamlarni bajaradi.
 */

// --------------------------------------------------------------------------- //
//  Tiplar
// --------------------------------------------------------------------------- //

export type Foydalanuvchi = {
  id: number;
  telegramId: number;
  username: string | null;
  fullName: string | null;
  language: string;
  isBlocked: boolean;
  declaredBalanceUsd: number | null;
};

export type Tarif = "lite" | "pro" | "premium";

export const TARIF_DARAJASI: Record<Tarif, number> = { lite: 1, pro: 2, premium: 3 };

/** Botdagi `SubscriptionTier.covers()` bilan bir xil mantiq. */
export function tarifQamraydi(bor: Tarif | null, kerak: Tarif): boolean {
  return bor !== null && TARIF_DARAJASI[bor] >= TARIF_DARAJASI[kerak];
}

export type Obuna = {
  id: number;
  tier: Tarif;
  period: string;
  status: string;
  expiresAt: Date | null;
  isTrial: boolean;
};

export type SignalHolati =
  | "pending"
  | "active"
  | "tp1_hit"
  | "tp2_hit"
  | "stopped"
  | "weakening"
  | "cancelled"
  | "timed_out";

export type Signal = {
  id: number;
  symbol: string;
  source: string;
  status: SignalHolati;
  entry: number;
  stop: number;
  tp1: number;
  /** TP SONI QAT'IY EMAS — 1, 2 yoki 3. Yo'qlari `null`. */
  tp2: number | null;
  tp3: number | null;
  /** Barcha TP narxlari, pastdan yuqoriga. Kartochka SHUNI o'qiydi:
   *  alohida maydonlarni sanab chiqish "har doim ikkita" degan
   *  taxminni har bir chaqiruv joyida takrorlardi. */
  tplar: number[];
  entryOrderType: string;
  score: number | null;
  halalReason: string | null;
  scoreBreakdown: string | null;
  marketHealthAtEntry: number | null;
  createdAt: Date | null;
  closedAt: Date | null;
  resultPct: number | null;
  /** TP1 ga bir marta yetganmi — Stop kirish narxiga ko'tarilgan bo'ladi */
  tp1Reached: boolean;
};

/** Botdagi `SignalStatus.is_enterable` — TP1 olgan yoki zaiflashgan
 *  signalga endi kirish kerak emas: Stopgacha masofa o'sha-o'sha, TPgacha
 *  esa qisqargan. Yangi foydalanuvchi buni o'zi hisoblamasligi kerak. */
export function kirishMumkin(holat: SignalHolati): boolean {
  return holat === "pending" || holat === "active";
}

/** Signal hali yuribdimi — YOPILMAGAN.
 *
 * `kirishMumkin` dan farqi bor va farq MUHIM: TP1 olingan signal
 * yangi kirish uchun yopiq, lekin unga ALLAQACHON KIRGAN odam uchun
 * u hali ham jonli — Stop kirish narxiga ko'tarilgani, grafik va
 * kalkulyator unga kerak. Ilgari sahifa shunday odamni ham
 * ro'yxatga qaytarib yuborardi.
 */
export function davomEtmoqda(holat: SignalHolati): boolean {
  return !yopilgan(holat);
}

/** Yopiq holatlar — BITTA MANBA.
 *
 * Ilgari bu ro'yxat ikki joyda alohida yozilgan edi: shu funksiyada va
 * `yopilganSignallar()` ning SQL so'rovida. Yangi yopuvchi holat
 * qo'shilganda ularning biri unutilsa, signal jadvalda ko'rinmay
 * qolardi yoki abadiy "ochiq" bo'lib turardi — va xato hech qayerda
 * xabar bermasdi. Botdagi `SignalStatus.closed_values()` bilan bir xil
 * qoida. */
export const YOPIQ_HOLATLAR = [
  "tp2_hit",
  "stopped",
  "cancelled",
  "timed_out",
] as const;

export function yopilgan(holat: SignalHolati): boolean {
  return (YOPIQ_HOLATLAR as readonly string[]).includes(holat);
}

export type Salomatlik = {
  value: number;
  band: string;
  /** ASOSIY omil (45) — SMC strukturasi bo'yicha kenglik */
  structureBreadthScore: number | null;
  btcDominanceScore: number | null;
  /** QT (AMDX) davri (5) */
  quarterlyPhaseScore: number | null;
  /** QT davri HARFI — bazadan o'qiladi, soatdan hisoblanmaydi */
  quarterlyPhase: string | null;
  volatilityScore: number | null;
  userCapacityScore: number | null;
  saturationScore: number | null;
  createdAt: Date | null;
};

export type Statistika = {
  signalsCreated: number;
  signalsActivated: number;
  tp1Count: number;
  tp2Count: number;
  stopCount: number;
  falseSignalCount: number;
  averageScore: number | null;
  averageRiskReward: number | null;
  participants: number;
  totalVolumeUsd: number;
};

export type Pozitsiya = {
  id: number;
  signalId: number;
  symbol: string;
  signalStatus: SignalHolati;
  amountUsd: number;
  entryPrice: number;
  exitPrice: number | null;
  pnlUsd: number | null;
  pnlPct: number | null;
  tradeDate: string;
  closedAt: Date | null;
};

export type VoronkaQatori = {
  stage: string;
  count: number;
  routine: boolean;
};

export type Kontent = {
  id: number;
  kind: string;
  title: string;
  description: string | null;
  minTier: Tarif;
  position: number;
  /** Saytga yuklangan fayl nomi. `null` — video hali yuklanmagan. */
  videoPath: string | null;
};

export type Narx = {
  tier: Tarif;
  period: string;
  currency: string;
  amount: number;
  paymentDetails: string | null;
};

export type KutilayotganTolov = {
  id: number;
  userId: number;
  telegramId: number;
  username: string | null;
  fullName: string | null;
  tier: Tarif;
  period: string;
  amount: number;
  currency: string;
  createdAt: Date | null;
  /** Telegramdagi chek rasmi. `null` — chek biriktirilmagan. */
  receiptFileId: string | null;
};

// --------------------------------------------------------------------------- //
//  Foydalanuvchi va obuna
// --------------------------------------------------------------------------- //

type Qator = Record<string, unknown>;

const son = (x: unknown): number | null =>
  typeof x === "number" ? x : x === null || x === undefined ? null : Number(x);

export function foydalanuvchiOl(telegramId: number): Foydalanuvchi | null {
  const q = db()
    .prepare(
      `select id, telegram_id, username, full_name, language, is_blocked,
              declared_balance_usd
         from users where telegram_id = ?`,
    )
    .get(telegramId) as Qator | undefined;
  if (!q) return null;
  return {
    id: Number(q.id),
    telegramId: Number(q.telegram_id),
    username: (q.username as string) ?? null,
    fullName: (q.full_name as string) ?? null,
    language: (q.language as string) ?? "uz",
    isBlocked: Boolean(q.is_blocked),
    declaredBalanceUsd: son(q.declared_balance_usd),
  };
}

/** Faol obuna. Botdagi `SubscriptionRepository.active_for` bilan bir xil
 *  shart: holati `active` VA muddati hali o'tmagan. */
export function faolObuna(userId: number, hozir = new Date()): Obuna | null {
  const q = db()
    .prepare(
      `select id, tier, period, status, expires_at, is_trial
         from subscriptions
        where user_id = ? and status = 'active' and expires_at > ?
        order by expires_at desc limit 1`,
    )
    .get(userId, vaqtSatri(hozir)) as Qator | undefined;
  if (!q) return null;
  return {
    id: Number(q.id),
    tier: q.tier as Tarif,
    period: q.period as string,
    status: q.status as string,
    expiresAt: vaqt(q.expires_at as string),
    isTrial: Boolean(q.is_trial),
  };
}

/** Muddati tugagan bo'lsa ham oxirgi obunani ko'rsatamiz — profilda
 *  "obunangiz falon kuni tugagan" deb yozish uchun. */
export function oxirgiObuna(userId: number): Obuna | null {
  const q = db()
    .prepare(
      `select id, tier, period, status, expires_at, is_trial
         from subscriptions where user_id = ?
        order by expires_at desc limit 1`,
    )
    .get(userId) as Qator | undefined;
  if (!q) return null;
  return {
    id: Number(q.id),
    tier: q.tier as Tarif,
    period: q.period as string,
    status: q.status as string,
    expiresAt: vaqt(q.expires_at as string),
    isTrial: Boolean(q.is_trial),
  };
}

export function kutilayotganTolovBor(userId: number): boolean {
  const q = db()
    .prepare(`select 1 from payments where user_id = ? and status = 'pending' limit 1`)
    .get(userId);
  return q !== undefined;
}

// --------------------------------------------------------------------------- //
//  Signallar
// --------------------------------------------------------------------------- //

function signalgaAylantir(q: Qator): Signal {
  return {
    id: Number(q.id),
    symbol: q.symbol as string,
    source: q.source as string,
    status: q.status as SignalHolati,
    entry: Number(q.entry),
    stop: Number(q.stop),
    tp1: Number(q.tp1),
    tp2: son(q.tp2),
    tp3: son(q.tp3),
    tplar: [q.tp1, q.tp2, q.tp3]
      .map((v) => son(v))
      .filter((v): v is number => v !== null),
    entryOrderType: (q.entry_order_type as string) ?? "limit",
    score: son(q.score),
    halalReason: (q.halal_reason as string) ?? null,
    scoreBreakdown: (q.score_breakdown as string) ?? null,
    marketHealthAtEntry: son(q.market_health_at_entry),
    createdAt: vaqt(q.created_at as string),
    closedAt: vaqt(q.closed_at as string),
    resultPct: son(q.result_pct),
    tp1Reached: Boolean(q.tp1_reached),
  };
}

const SIGNAL_USTUNLARI = `id, symbol, source, status, entry, stop, tp1, tp2, tp3,
  entry_order_type, score, halal_reason, score_breakdown,
  market_health_at_entry, created_at, closed_at, result_pct, tp1_reached`;

export function signallar(limit = 50): Signal[] {
  const qatorlar = db()
    .prepare(`select ${SIGNAL_USTUNLARI} from signals order by created_at desc limit ?`)
    .all(limit) as Qator[];
  return qatorlar.map(signalgaAylantir);
}

export function signalOl(id: number): Signal | null {
  const q = db()
    .prepare(`select ${SIGNAL_USTUNLARI} from signals where id = ?`)
    .get(id) as Qator | undefined;
  return q ? signalgaAylantir(q) : null;
}

// --------------------------------------------------------------------------- //
//  Bozor Salomatligi
// --------------------------------------------------------------------------- //

function salomatlikkaAylantir(q: Qator): Salomatlik {
  return {
    value: Number(q.value),
    band: q.band as string,
    structureBreadthScore: son(q.structure_breadth_score),
    btcDominanceScore: son(q.btc_dominance_score),
    quarterlyPhaseScore: son(q.quarterly_phase_score),
    quarterlyPhase: (q.quarterly_phase as string) ?? null,
    volatilityScore: son(q.volatility_score),
    userCapacityScore: son(q.user_capacity_score),
    saturationScore: son(q.saturation_score),
    createdAt: vaqt(q.created_at as string),
  };
}

// `trend_breadth_score` ustuni bazada QOLADI (eski yozuvlarda ma'lumot
// bor), lekin o'qilmaydi: EMA asosidagi kenglik omili olib tashlandi.
const SALOMATLIK_USTUNLARI = `value, band, structure_breadth_score,
  btc_dominance_score, quarterly_phase_score, quarterly_phase,
  volatility_score, user_capacity_score,
  saturation_score, created_at`;

/** Kunlik "oldindan ko'rish" yozuvlari chiqarib tashlanadi — ular
 *  bashorat, o'lchov emas (`is_daily_preview`). */


// --------------------------------------------------------------------------- //
//  Statistika
// --------------------------------------------------------------------------- //

/** Botdagi `DailyStatsRepository.aggregate` bilan BIR XIL hisob.
 *
 * Nima uchun aynan bir xil: topshiriq "botdagi 📊 Statistika bilan bir xil
 * ma'lumot" deydi. Ikki joyda ikki xil hisoblansa, foydalanuvchi ikkita
 * turli raqam ko'radi va ikkalasiga ham ishonmay qo'yadi.
 */
export function statistika(sinceISO: string | null): Statistika {
  const shart = sinceISO ? `where date(created_at) >= ?` : "";
  const args = sinceISO ? [sinceISO] : [];

  const signallar = db()
    .prepare(`select status, score, entry, stop, tp2, activated_at, is_false_signal
                from signals ${shart}`)
    .all(...args) as Qator[];

  const pozShart = sinceISO ? `where trade_date >= ?` : "";
  const poz = db()
    .prepare(
      `select count(distinct user_id) as ishtirokchi,
              coalesce(sum(amount_usd), 0) as hajm
         from user_positions ${pozShart}`,
    )
    .get(...args) as Qator;

  const ballar = signallar.map((s) => son(s.score)).filter((x): x is number => x !== null);
  const rrLar = signallar
    .filter((s) => Number(s.entry) > Number(s.stop))
    .map((s) => (Number(s.tp2) - Number(s.entry)) / (Number(s.entry) - Number(s.stop)));

  const sanoq = (holat: string) => signallar.filter((s) => s.status === holat).length;
  const ortacha = (xs: number[]) =>
    xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;

  return {
    signalsCreated: signallar.length,
    signalsActivated: signallar.filter((s) => s.activated_at !== null).length,
    tp1Count: sanoq("tp1_hit"),
    tp2Count: sanoq("tp2_hit"),
    stopCount: sanoq("stopped"),
    falseSignalCount: signallar.filter((s) => Boolean(s.is_false_signal)).length,
    averageScore: ortacha(ballar),
    averageRiskReward: ortacha(rrLar),
    participants: Number(poz.ishtirokchi ?? 0),
    totalVolumeUsd: Number(poz.hajm ?? 0),
  };
}

// --------------------------------------------------------------------------- //
//  Portfel
// --------------------------------------------------------------------------- //

export function pozitsiyalar(userId: number): Pozitsiya[] {
  const qatorlar = db()
    .prepare(
      `select p.id, p.signal_id, p.amount_usd, p.entry_price, p.exit_price,
              p.pnl_usd, p.pnl_pct, p.trade_date, p.closed_at,
              s.symbol, s.status as signal_status
         from user_positions p
         join signals s on s.id = p.signal_id
        where p.user_id = ?
        order by p.trade_date desc, p.id desc`,
    )
    .all(userId) as Qator[];
  return qatorlar.map((q) => ({
    id: Number(q.id),
    signalId: Number(q.signal_id),
    symbol: q.symbol as string,
    signalStatus: q.signal_status as SignalHolati,
    amountUsd: Number(q.amount_usd),
    entryPrice: Number(q.entry_price),
    exitPrice: son(q.exit_price),
    pnlUsd: son(q.pnl_usd),
    pnlPct: son(q.pnl_pct),
    tradeDate: String(q.trade_date),
    closedAt: vaqt(q.closed_at as string),
  }));
}

// --------------------------------------------------------------------------- //
//  "Nega signal yo'q?" voronkasi
// --------------------------------------------------------------------------- //


/** Ball chegarasida to'xtaganlarning ball statistikasi.
 *
 * Bu raqamlarsiz "chegara juda balandmi yoki nomzodlar zaifmi" degan
 * savolga javob bo'lmaydi — dashboard faqat "chegaradan past" deb
 * yozardi. Aynan shu ko'rlik sababli chegara 48 soat davomida erishib
 * bo'lmas darajada balandligi sezilmagan edi.
 */

// --------------------------------------------------------------------------- //
//  Kontent va narxlar
// --------------------------------------------------------------------------- //

export function kontent(): Kontent[] {
  const qatorlar = db()
    .prepare(
      `select id, kind, title, description, min_tier, position, video_path
         from content where is_published = 1
        order by position asc, id asc`,
    )
    .all() as Qator[];
  return qatorlar.map((q) => ({
    id: Number(q.id),
    kind: q.kind as string,
    title: q.title as string,
    description: (q.description as string) ?? null,
    minTier: q.min_tier as Tarif,
    position: Number(q.position),
    videoPath: (q.video_path as string) ?? null,
  }));
}

export function narxlar(): Narx[] {
  const qatorlar = db()
    .prepare(
      `select tier, period, currency, amount, payment_details
         from price_config where is_active = 1
        order by tier, period, currency`,
    )
    .all() as Qator[];
  return qatorlar.map((q) => ({
    tier: q.tier as Tarif,
    period: q.period as string,
    currency: q.currency as string,
    amount: Number(q.amount),
    paymentDetails: (q.payment_details as string) ?? null,
  }));
}

// --------------------------------------------------------------------------- //
//  Admin: to'lovlar
// --------------------------------------------------------------------------- //

export function kutilayotganTolovlar(limit = 20): KutilayotganTolov[] {
  const qatorlar = db()
    .prepare(
      `select p.id, p.user_id, p.tier, p.period, p.amount, p.currency, p.created_at,
              p.receipt_file_id, u.telegram_id, u.username, u.full_name
         from payments p join users u on u.id = p.user_id
        where p.status = 'pending'
        order by p.created_at asc limit ?`,
    )
    .all(limit) as Qator[];
  return qatorlar.map((q) => ({
    id: Number(q.id),
    userId: Number(q.user_id),
    telegramId: Number(q.telegram_id),
    username: (q.username as string) ?? null,
    fullName: (q.full_name as string) ?? null,
    receiptFileId: (q.receipt_file_id as string) ?? null,
    tier: q.tier as Tarif,
    period: q.period as string,
    amount: Number(q.amount),
    currency: q.currency as string,
    createdAt: vaqt(q.created_at as string),
  }));
}

export type TolovNatijasi =
  | { ok: true; telegramId: number; expiresAt: Date }
  | { ok: false; sabab: "topilmadi" | "allaqachon" };

/** To'lovni tasdiqlaydi va obunani ochadi.
 *
 * Botdagi `SubscriptionService.approve_payment` bilan BIR XIL qadamlar:
 *   1. holat `pending` ekanini tekshirish (ikki marta tasdiqlanmasin)
 *   2. obuna yozuvini yaratish (muddat YAML dagi kunlar soniga qarab)
 *   3. to'lovni `approved` qilish va kim/qachon ko'rganini yozish
 *
 * Hammasi BITTA tranzaksiyada: yarmi bajarilib qolsa, foydalanuvchi
 * to'lovi "tasdiqlangan" bo'lib turadi-yu, obunasi ochilmaydi.
 */
export function tolovniTasdiqla(
  paymentId: number,
  adminTelegramId: number,
  hozir = new Date(),
): TolovNatijasi {
  const baza = db();

  // Tranzaksiya QO'LDA boshqariladi: `node:sqlite` da `better-sqlite3`
  // dagi `transaction()` o'ramchisi yo'q. Mantiq o'sha-o'sha — yarmi
  // bajarilib qolsa, to'lov "tasdiqlangan" bo'lib turadi-yu, obuna
  // ochilmaydi.
  baza.exec("BEGIN");
  try {
    const tolov = baza
      .prepare(
        `select p.id, p.user_id, p.tier, p.period, p.status, u.telegram_id
           from payments p join users u on u.id = p.user_id where p.id = ?`,
      )
      .get(paymentId) as Qator | undefined;

    if (!tolov) {
      baza.exec("ROLLBACK");
      return { ok: false, sabab: "topilmadi" };
    }
    if (tolov.status !== "pending") {
      baza.exec("ROLLBACK");
      return { ok: false, sabab: "allaqachon" };
    }

    const kunlar = obunaKunlari();
    const trial = tolov.period === "daily";
    const kun = trial ? kunlar.daily : kunlar.monthly;
    const tugash = new Date(hozir.getTime() + kun * 24 * 60 * 60 * 1000);

    const natija = baza
      .prepare(
        `insert into subscriptions
           (user_id, tier, period, status, starts_at, expires_at, is_trial,
            created_at, updated_at)
         values (?, ?, ?, 'active', ?, ?, ?, ?, ?)`,
      )
      .run(
        songaAylantir(tolov.user_id),
        String(tolov.tier),
        trial ? "daily" : "monthly",
        vaqtSatri(hozir),
        vaqtSatri(tugash),
        trial ? 1 : 0,
        vaqtSatri(hozir),
        vaqtSatri(hozir),
      );

    baza
      .prepare(
        `update payments
            set status = 'approved', reviewed_by = ?, reviewed_at = ?,
                subscription_id = ?, updated_at = ?
          where id = ?`,
      )
      .run(
        adminTelegramId,
        vaqtSatri(hozir),
        songaAylantir(natija.lastInsertRowid),
        vaqtSatri(hozir),
        paymentId,
      );

    baza.exec("COMMIT");
    return { ok: true, telegramId: songaAylantir(tolov.telegram_id), expiresAt: tugash };
  } catch (e) {
    baza.exec("ROLLBACK");
    throw e;
  }
}

export function tolovniRadEt(
  paymentId: number,
  adminTelegramId: number,
  sabab: string,
  hozir = new Date(),
): TolovNatijasi {
  const baza = db();
  const tolov = baza
    .prepare(
      `select p.status, u.telegram_id from payments p
         join users u on u.id = p.user_id where p.id = ?`,
    )
    .get(paymentId) as Qator | undefined;
  if (!tolov) return { ok: false, sabab: "topilmadi" };
  if (tolov.status !== "pending") return { ok: false, sabab: "allaqachon" };

  baza
    .prepare(
      `update payments
          set status = 'rejected', reviewed_by = ?, reviewed_at = ?,
              reject_reason = ?, updated_at = ?
        where id = ?`,
    )
    .run(adminTelegramId, vaqtSatri(hozir), sabab, vaqtSatri(hozir), paymentId);

  return { ok: true, telegramId: songaAylantir(tolov.telegram_id), expiresAt: hozir };
}

// --------------------------------------------------------------------------- //
//  Kirish paytida foydalanuvchini yozib qo'yish
// --------------------------------------------------------------------------- //

/** Botdagi `UserRepository.get_or_create` bilan bir xil xatti-harakat.
 *
 * Diqqat: `role` HAR SAFAR qayta yoziladi. Admin ro'yxati `.env` da
 * boshqariladi, shuning uchun u yerdan olib tashlangan odam bazada admin
 * bo'lib qolmasligi kerak — botdagi izoh ham aynan shu haqda.
 */
export function foydalanuvchiniYozib(
  telegramId: number,
  username: string | null,
  fullName: string | null,
  admin: boolean,
  hozir = new Date(),
): Foydalanuvchi {
  const baza = db();
  const rol = admin ? "admin" : "user";
  const vaqtNow = vaqtSatri(hozir);
  const mavjud = foydalanuvchiOl(telegramId);

  if (!mavjud) {
    baza
      .prepare(
        `insert into users (telegram_id, username, full_name, role, language,
                            is_blocked, last_active_at, created_at, updated_at)
         values (?, ?, ?, ?, 'uz', 0, ?, ?, ?)`,
      )
      .run(telegramId, username, fullName, rol, vaqtNow, vaqtNow, vaqtNow);
  } else {
    baza
      .prepare(
        `update users set username = coalesce(?, username),
                          full_name = coalesce(?, full_name),
                          role = ?, last_active_at = ?, updated_at = ?
          where telegram_id = ?`,
      )
      .run(username, fullName, rol, vaqtNow, vaqtNow, telegramId);
  }
  return foydalanuvchiOl(telegramId)!;
}

// --------------------------------------------------------------------------- //
//  Admin: Signal Xotirasi hisoboti (3.8-band)
// --------------------------------------------------------------------------- //

export type Hisobot = {
  id: number;
  generatedAt: Date | null;
  periodDays: number;
  rendered: string;
  total: number;
  traded: number;
  tp2: number;
  tp1ThenStop: number;
  stop: number;
  cancelled: number;
  falseSignals: number;
  averageScore: number | null;
  averageHoldingHours: number | null;
  patternCount: number;
  sampleWarning: string | null;
};

/** Hisobotni SAYT HISOBLAMAYDI — u `core/analysis/postmortem/` da
 *  hisoblanib, bot tomonidan bazaga yozilgan. Naqsh tahlilini bu yerda
 *  qayta yozish "bitta manba" qoidasini buzardi: ikki joyda ikki xil
 *  natija chiqishi mumkin edi. */
export type YopilganSignal = {
  id: number;
  symbol: string;
  source: string;
  status: SignalHolati;
  entry: number;
  stop: number;
  tp2: number;
  score: number | null;
  marketHealthAtEntry: number | null;
  resultPct: number | null;
  tp1Reached: boolean;
  isFalseSignal: boolean;
  createdAt: Date | null;
  closedAt: Date | null;
};

/** Yopilgan signallar — HAR BIRI alohida qator.
 *
 * NIMA UCHUN KERAK: naqsh izlash 12 ta namunadan boshlanadi
 * (`postmortem.min_sample_size`), sinovning birinchi haftalarida esa
 * signal bundan kam. Ya'ni "Signal Xotirasi" hali jim turadi va
 * admin qo'lida hech qanday raqam qolmaydi.
 *
 * Bu ro'yxat BIRINCHI signaldan boshlab ishlaydi: har bir savdoning
 * kirish sharti (ball, salomatlik), va'dasi (R/R) va yakuni yonma-yon
 * turadi. 100 kunlik sinovda "qaysi shart g'olibni yutqazgandan
 * ajratadi" degan savolga xom material shu.
 */
export function yopilganSignallar(limit = 50): YopilganSignal[] {
  const qatorlar = db()
    .prepare(
      `select id, symbol, source, status, entry, stop, tp2, score,
              market_health_at_entry, result_pct, tp1_reached, is_false_signal,
              created_at, closed_at
         from signals
        where status in (${YOPIQ_HOLATLAR.map(() => "?").join(", ")})
        order by closed_at desc, id desc
        limit ?`,
    )
    .all(...YOPIQ_HOLATLAR, limit) as Qator[];

  return qatorlar.map((q) => ({
    id: Number(q.id),
    symbol: q.symbol as string,
    source: q.source as string,
    status: q.status as SignalHolati,
    entry: Number(q.entry),
    stop: Number(q.stop),
    tp2: Number(q.tp2),
    score: son(q.score),
    marketHealthAtEntry: son(q.market_health_at_entry),
    resultPct: son(q.result_pct),
    tp1Reached: Boolean(q.tp1_reached),
    isFalseSignal: Boolean(q.is_false_signal),
    createdAt: vaqt(q.created_at as string),
    closedAt: vaqt(q.closed_at as string),
  }));
}


// --------------------------------------------------------------------------- //
//  Admin: narxlar (1.2-band)
// --------------------------------------------------------------------------- //

export type NarxNatijasi = { ok: true } | { ok: false; sabab: string };

/** Botdagi `PriceRepository.upsert` bilan bir xil qoidalar.
 *
 * Manfiy yoki nol narx RAD ETILADI: botda ham shunday. Aks holda sayt
 * orqali 0 so'mlik tarif yaratib qo'yish mumkin bo'lardi va buni hech
 * kim sezmasdi.
 */
export function narxniYangila(
  tier: Tarif,
  period: string,
  currency: string,
  amount: number,
  paymentDetails: string | null,
  hozir = new Date(),
): NarxNatijasi {
  if (!Number.isFinite(amount) || amount <= 0) {
    return { ok: false, sabab: "Narx musbat son bo'lishi kerak" };
  }
  if (!["daily", "monthly"].includes(period)) {
    return { ok: false, sabab: `Noma'lum muddat: ${period}` };
  }

  const baza = db();
  const vaqtNow = vaqtSatri(hozir);
  const mavjud = baza
    .prepare(
      `select id from price_config where tier = ? and period = ? and currency = ?`,
    )
    .get(tier, period, currency) as Qator | undefined;

  if (mavjud) {
    baza
      .prepare(
        `update price_config
            set amount = ?,
                payment_details = coalesce(?, payment_details),
                is_active = 1, updated_at = ?
          where id = ?`,
      )
      .run(amount, paymentDetails, vaqtNow, songaAylantir(mavjud.id));
  } else {
    baza
      .prepare(
        `insert into price_config (tier, period, currency, amount, payment_details,
                                   is_active, created_at, updated_at)
         values (?, ?, ?, ?, ?, 1, ?, ?)`,
      )
      .run(tier, period, currency, amount, paymentDetails, vaqtNow, vaqtNow);
  }
  return { ok: true };
}

// --------------------------------------------------------------------------- //
//  Admin: halol ro'yxat (1.4 / 3.4-band)
// --------------------------------------------------------------------------- //

export type HalolHolat = "halal" | "mashbooh" | "haram";

export type CoinQarori = {
  symbol: string;
  status: HalolHolat;
  reason: string;
  source: string | null;
  setBy: number | null;
  updatedAt: Date | null;
};

export function coinQarorlari(): CoinQarori[] {
  const qatorlar = db()
    .prepare(
      `select symbol, status, reason, source, set_by, updated_at
         from coin_rulings order by status, symbol`,
    )
    .all() as Qator[];
  return qatorlar.map((q) => ({
    symbol: q.symbol as string,
    status: q.status as HalolHolat,
    reason: q.reason as string,
    source: (q.source as string) ?? null,
    setBy: son(q.set_by),
    updatedAt: vaqt(q.updated_at as string),
  }));
}

export type QarorNatijasi = { ok: true } | { ok: false; sabab: string };

/** Coin qarorini belgilaydi yoki yangilaydi.
 *
 * `reason` MAJBURIY va bo'sh bo'lishi mumkin emas — botda ham shunday
 * (`CoinRuling.reason` nullable emas). Sabab yozilmasa, oradan olti oy
 * o'tib "bu coin nega harom deb belgilangan?" degan savolga javob
 * qolmaydi.
 */
export function coinQaroriniBelgila(
  symbol: string,
  status: HalolHolat,
  reason: string,
  adminTelegramId: number,
  hozir = new Date(),
): QarorNatijasi {
  const belgi = symbol.trim().toUpperCase();
  if (!/^[A-Z0-9]{2,32}$/.test(belgi)) {
    return { ok: false, sabab: "Symbol faqat harf va raqamdan iborat bo'lsin" };
  }
  const sabab = reason.trim();
  if (!sabab) return { ok: false, sabab: "Sabab yozilishi shart" };
  if (!["halal", "mashbooh", "haram"].includes(status)) {
    return { ok: false, sabab: `Noma'lum holat: ${status}` };
  }

  const baza = db();
  const vaqtNow = vaqtSatri(hozir);
  const mavjud = baza
    .prepare(`select id from coin_rulings where symbol = ?`)
    .get(belgi) as Qator | undefined;

  if (mavjud) {
    baza
      .prepare(
        `update coin_rulings set status = ?, reason = ?, set_by = ?, updated_at = ?
          where id = ?`,
      )
      .run(status, sabab, adminTelegramId, vaqtNow, songaAylantir(mavjud.id));
  } else {
    baza
      .prepare(
        `insert into coin_rulings (symbol, status, reason, source, set_by,
                                   created_at, updated_at)
         values (?, ?, ?, 'sayt', ?, ?, ?)`,
      )
      .run(belgi, status, sabab, adminTelegramId, vaqtNow, vaqtNow);
  }
  return { ok: true };
}

export function coinQaroriniOchir(symbol: string): boolean {
  const natija = db()
    .prepare(`delete from coin_rulings where symbol = ?`)
    .run(symbol.trim().toUpperCase());
  return natija.changes > 0;
}

// --------------------------------------------------------------------------- //
//  Admin: qo'lda signal kiritish (2-bo'lim)
// --------------------------------------------------------------------------- //

export type SignalKirish = {
  symbol: string;
  entry: number;
  stop: number;
  tp1: number;
  tp2: number;
  note: string | null;
};

export type SignalNatijasi =
  | { ok: true; id: number; ogohlantirishlar: string[] }
  | { ok: false; sabab: string };

/** Darajalar TARTIBI — bu ta'rif, chegara emas.
 *
 * Spot (long) savdoda Stop kirishdan past, TP lar esa yuqori bo'lishi
 * SHART. Botdagi `SignalLevels` ham aynan shuni tekshiradi va
 * `ValueError` beradi. Bu qoida hech qachon o'zgarmaydi — shuning uchun
 * uni konfiguratsiyadan o'qish shart emas.
 */
function tartibXatosi(k: SignalKirish): string | null {
  for (const [nom, qiymat] of [
    ["Kirish", k.entry],
    ["Stop", k.stop],
    ["TP1", k.tp1],
    ["TP2", k.tp2],
  ] as const) {
    if (!Number.isFinite(qiymat) || qiymat <= 0) return `${nom} musbat son bo'lishi kerak`;
  }
  if (k.stop >= k.entry) return "Stop kirish narxidan PAST bo'lishi kerak";
  if (k.tp1 <= k.entry) return "TP1 kirish narxidan YUQORI bo'lishi kerak";
  if (k.tp2 <= k.tp1) return "TP2 TP1 dan yuqori bo'lishi kerak";
  return null;
}

/** Botdagi `_rule_warnings` bilan bir xil tekshiruvlar.
 *
 * TAQIQ EMAS, ogohlantirish: qo'lda kiritilgan signalda 3.3-band
 * qoidalari majburiy emas — admin bilib turib chetga chiqishi mumkin.
 */
export function signalOgohlantirishlari(k: SignalKirish): string[] {
  const q = savdoQoidalari();
  const ogohlar: string[] = [];

  const stopMasofa = ((k.entry - k.stop) / k.entry) * 100;
  if (stopMasofa > q.maxStopPct) {
    ogohlar.push(`Stop masofasi ${stopMasofa.toFixed(2)}% (chegara ${q.maxStopPct}%)`);
  }
  for (const [nom, narx] of [
    ["TP1", k.tp1],
    ["TP2", k.tp2],
  ] as const) {
    const masofa = ((narx - k.entry) / k.entry) * 100;
    if (masofa < q.minTpPct || masofa > q.maxTpPct) {
      ogohlar.push(
        `${nom} masofasi ${masofa.toFixed(2)}% (${q.minTpPct}–${q.maxTpPct}% oralig'idan tashqarida)`,
      );
    }
  }
  // BOG'LOVCHI SHART — nisbat. Foiz oraliqlari majburiy emas
  // (loyiha egasining qarori), lekin ogohlantirish sifatida qoladi.
  const rr = (k.tp2 - k.entry) / (k.entry - k.stop);
  if (rr < q.minRiskReward) {
    ogohlar.push(`Yakuniy nishon R/R ${rr.toFixed(2)} < ${q.minRiskReward}`);
  }
  return ogohlar;
}

/** Signalni bazaga yozadi. TARQATMAYDI.
 *
 * Tarqatish ATAYLAB bu yerda emas: kartochka har bir obunachi uchun
 * alohida yasaladi (miqdor uning balansidan hisoblanadi) va
 * `protect_content=True` bilan yuboriladi. Buni TypeScriptda takrorlash
 * kartochka mantig'ining ikkinchi nusxasi bo'lardi.
 *
 * Shuning uchun `broadcast_at` bo'sh qoldiriladi — bot uni bir daqiqa
 * ichida topib, kuzatuvga oladi va obunachilarga yuboradi
 * (`bot/services/scheduler.py`, "web-signals" vazifasi).
 */
export function signalYarat(
  kirish: SignalKirish,
  hozir = new Date(),
): SignalNatijasi {
  // ASOSIY AKTIVGA keltiriladi: bazada `symbol` — `DOT`, `DOTUSDT`
  // emas (bot ham shunday yozadi). Admin juftlikni to'liq yozib
  // yuborsa, o'sha bitta ustunda ikki xil shakl paydo bo'lardi va
  // grafik ham, kuzatuv ham qaysi biriga ishonishni bilmasdi.
  const xomSymbol = kirish.symbol.trim().toUpperCase();
  if (!/^[A-Z0-9]{2,32}$/.test(xomSymbol)) {
    return { ok: false, sabab: "Symbol faqat harf va raqamdan iborat bo'lsin" };
  }
  const symbol = asosiyAktiv(xomSymbol, kotirovka());
  const k = { ...kirish, symbol };
  const xato = tartibXatosi(k);
  if (xato) return { ok: false, sabab: xato };

  const vaqtNow = vaqtSatri(hozir);
  const natija = db()
    .prepare(
      `insert into signals
         (symbol, source, status, entry, stop, tp1, tp2, entry_order_type,
          exit_order_type, note, is_false_signal, created_at, updated_at)
       values (?, 'manual', 'pending', ?, ?, ?, ?, 'limit', 'oco', ?, 0, ?, ?)`,
    )
    .run(symbol, k.entry, k.stop, k.tp1, k.tp2, k.note, vaqtNow, vaqtNow);

  return {
    ok: true,
    id: songaAylantir(natija.lastInsertRowid),
    ogohlantirishlar: signalOgohlantirishlari(k),
  };
}

/** Hali tarqatilmagan signallar — panelda "yuborilmoqda" deb ko'rsatiladi. */
export function tarqatilmaganSignallar(): { id: number; symbol: string; createdAt: Date | null }[] {
  const qatorlar = db()
    .prepare(
      `select id, symbol, created_at from signals
        where broadcast_at is null and status in ('pending','active','tp1_hit','weakening')
        order by created_at`,
    )
    .all() as Qator[];
  return qatorlar.map((q) => ({
    id: songaAylantir(q.id),
    symbol: q.symbol as string,
    createdAt: vaqt(q.created_at as string),
  }));
}

/** Barcha signallar — admin ro'yxati uchun (o'chirish tugmasi bilan). */
export function adminSignallar(limit = 100): {
  id: number;
  symbol: string;
  status: SignalHolati;
  entry: number;
  resultPct: number | null;
  createdAt: Date | null;
  broadcast: boolean;
}[] {
  const qatorlar = db()
    .prepare(
      `select id, symbol, status, entry, result_pct, created_at, broadcast_at
         from signals order by created_at desc, id desc limit ?`,
    )
    .all(limit) as Qator[];
  return qatorlar.map((q) => ({
    id: songaAylantir(q.id),
    symbol: q.symbol as string,
    status: q.status as SignalHolati,
    entry: Number(q.entry),
    resultPct: q.result_pct === null ? null : Number(q.result_pct),
    createdAt: vaqt(q.created_at as string),
    broadcast: q.broadcast_at !== null,
  }));
}

/** Signalni va unga bog'liq hamma narsani o'chiradi.
 *
 * NEGA HAQIQIY O'CHIRISH (yashirish emas): bu amal SINOV signallari
 * uchun. Ular statistikaga kiradi va uni buzadi — bitta soxta "-94%"
 * butun g'alaba foizini yaroqsiz qiladi. Yashirilgan signal esa
 * hisob-kitobda qolaverardi.
 *
 * NEGA BOG'LIQ YOZUVLAR QO'LDA O'CHIRILADI: sxemada ular
 * `ondelete="CASCADE"` bilan bog'langan, LEKIN SQLite'da tashqi
 * kalitlar STANDART HOLDA O'CHIQ (`PRAGMA foreign_keys = 0`) —
 * tekshirildi, bu bazada ham shunday. Ya'ni CASCADE umuman
 * ishlamaydi va faqat `signals` dan o'chirsak, `user_positions`
 * yetim qolardi: foydalanuvchining portfeli va statistikasi mavjud
 * bo'lmagan signalga ishora qilib turardi.
 *
 * Pragmani yoqish o'rniga qo'lda o'chirish tanlandi: pragma butun
 * ulanishga ta'sir qiladi va bot yozayotgan boshqa yo'llarni
 * kutilmaganda buzishi mumkin. Bu yerdagi uchta `delete` esa faqat
 * shu amalga tegishli.
 *
 * Qaytadi: o'chirildimi.
 */
export function signalOchir(id: number): boolean {
  const baza = db();
  baza.exec("BEGIN");
  try {
    baza.prepare(`delete from signal_events where signal_id = ?`).run(id);
    baza.prepare(`delete from user_positions where signal_id = ?`).run(id);
    const natija = baza.prepare(`delete from signals where id = ?`).run(id);
    baza.exec("COMMIT");
    return songaAylantir(natija.changes) > 0;
  } catch (xato) {
    baza.exec("ROLLBACK");
    throw xato;
  }
}

// --------------------------------------------------------------------------- //
//  Admin: video darsliklar (1.5-band)
// --------------------------------------------------------------------------- //

export type DarsKirish = {
  title: string;
  description: string | null;
  minTier: Tarif;
  position: number;
  fileId: string | null;
  published: boolean;
};

export function darslar(): (Kontent & { fileId: string | null; published: boolean })[] {
  const qatorlar = db()
    .prepare(
      `select id, kind, title, description, min_tier, position, file_id,
              video_path, is_published
         from content order by position asc, id asc`,
    )
    .all() as Qator[];
  return qatorlar.map((q) => ({
    id: songaAylantir(q.id),
    kind: q.kind as string,
    title: q.title as string,
    description: (q.description as string) ?? null,
    minTier: q.min_tier as Tarif,
    position: songaAylantir(q.position),
    fileId: (q.file_id as string) ?? null,
    videoPath: (q.video_path as string) ?? null,
    published: Boolean(q.is_published),
  }));
}

/** Foydalanuvchi e'lon qilgan balansi (5.1-band).
 *
 * "E'LON QILGAN" — bu birja hisobiga ULANMAGAN raqam, foydalanuvchi
 * o'zi aytadi. Tizim undan faqat pozitsiya hajmini taklif qilish uchun
 * foydalanadi va hech qachon uni tekshira olmaydi. Shuning uchun nom
 * ham shunday: `declared_balance_usd`.
 *
 * `null` — balansni O'CHIRISH (foydalanuvchi ko'rsatmaslikni tanladi),
 * bu 0 dan farq qiladi: 0 "pulim yo'q" degani, `null` esa "aytmayman".
 */
export function balansSaqla(
  userId: number,
  summa: number | null,
  hozir = new Date(),
): { ok: true } | { ok: false; sabab: string } {
  if (summa !== null && (!Number.isFinite(summa) || summa < 0)) {
    return { ok: false, sabab: "Balans manfiy bo'lishi mumkin emas" };
  }
  const natija = db()
    .prepare(`update users set declared_balance_usd = ?, updated_at = ? where id = ?`)
    .run(summa, vaqtSatri(hozir), userId);
  if (songaAylantir(natija.changes) === 0) {
    return { ok: false, sabab: "Foydalanuvchi topilmadi" };
  }
  return { ok: true };
}

/** Foydalanuvchining shu signaldagi pozitsiyasi (bo'lsa). */
export function pozitsiyaOl(
  userId: number,
  signalId: number,
): { amountUsd: number; entryPrice: number } | null {
  const q = db()
    .prepare(
      `select amount_usd, entry_price from user_positions
        where user_id = ? and signal_id = ?`,
    )
    .get(userId, signalId) as Qator | undefined;
  if (!q) return null;
  return { amountUsd: Number(q.amount_usd), entryPrice: Number(q.entry_price) };
}

/** "Men sotib oldim" — pozitsiyani qayd etadi (5.4-band).
 *
 * QOIDALAR BOTDAGI BILAN BIR XIL (`bot/handlers/portfolio.py`):
 *   - yopilgan signalga kirib bo'lmaydi;
 *   - bitta signalga bir marta;
 *   - miqdor `portfolio.min_position_usd` dan kam bo'lmasin.
 *
 * KIRISH NARXI FORMADAN OLINMAYDI — signal yozuvidan olinadi.
 * Aks holda foydalanuvchi o'ziga qulay narx yozib, keyin
 * statistikada mavjud bo'lmagan foyda ko'rsatardi.
 */
export function pozitsiyaQayd(
  userId: number,
  signalId: number,
  summa: number,
  hozir = new Date(),
): { ok: true } | { ok: false; sabab: string } {
  const eng = engKichikPozitsiya();
  if (!Number.isFinite(summa) || summa < eng) {
    return { ok: false, sabab: `Miqdor kamida $${eng} bo'lishi kerak` };
  }

  const s = signalOl(signalId);
  if (!s) return { ok: false, sabab: "Signal topilmadi" };
  if (yopilgan(s.status)) return { ok: false, sabab: "Bu signal allaqachon yopilgan" };

  if (pozitsiyaOl(userId, signalId) !== null) {
    return { ok: false, sabab: "Siz bu signalga allaqachon kirgansiz" };
  }

  const vaqtNow = vaqtSatri(hozir);
  db()
    .prepare(
      `insert into user_positions
         (user_id, signal_id, amount_usd, entry_price, trade_date, created_at, updated_at)
       values (?, ?, ?, ?, ?, ?, ?)`,
    )
    .run(userId, signalId, summa, s.entry, vaqtNow.slice(0, 10), vaqtNow, vaqtNow);
  return { ok: true };
}

export type DarsNatijasi = { ok: true; id: number } | { ok: false; sabab: string };

export function darsSaqla(
  id: number | null,
  kirish: DarsKirish,
  hozir = new Date(),
): DarsNatijasi {
  const title = kirish.title.trim();
  if (!title) return { ok: false, sabab: "Sarlavha yozilishi shart" };
  if (!["lite", "pro", "premium"].includes(kirish.minTier)) {
    return { ok: false, sabab: `Noma'lum tarif: ${kirish.minTier}` };
  }

  const baza = db();
  const vaqtNow = vaqtSatri(hozir);
  const tavsif = kirish.description?.trim() || null;
  const fileId = kirish.fileId?.trim() || null;

  if (id !== null) {
    baza
      .prepare(
        `update content
            set title = ?, description = ?, min_tier = ?, position = ?,
                file_id = coalesce(?, file_id), is_published = ?, updated_at = ?
          where id = ?`,
      )
      .run(title, tavsif, kirish.minTier, kirish.position, fileId,
           kirish.published ? 1 : 0, vaqtNow, id);
    return { ok: true, id };
  }

  const natija = baza
    .prepare(
      `insert into content (kind, title, description, file_id, min_tier, position,
                            is_published, created_at, updated_at)
       values ('video', ?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .run(title, tavsif, fileId, kirish.minTier, kirish.position,
         kirish.published ? 1 : 0, vaqtNow, vaqtNow);
  return { ok: true, id: songaAylantir(natija.lastInsertRowid) };
}

export function darsOchir(id: number): boolean {
  return db().prepare(`delete from content where id = ?`).run(id).changes > 0;
}

/** Bitta dars — yuklangan videoni berishdan oldin tekshirish uchun.
 *
 * `is_published` ham qaytariladi: chop etilmagan darsning videosini
 * manzilni qo'lda yozib olib bo'lmasin. */
export function dars(id: number): {
  id: number;
  title: string;
  minTier: Tarif;
  videoPath: string | null;
  published: boolean;
} | null {
  const q = db()
    .prepare(
      `select id, title, min_tier, video_path, is_published
         from content where id = ?`,
    )
    .get(id) as Qator | undefined;
  if (!q) return null;
  return {
    id: songaAylantir(q.id),
    title: q.title as string,
    minTier: q.min_tier as Tarif,
    videoPath: (q.video_path as string) ?? null,
    published: Boolean(q.is_published),
  };
}

/** Yuklangan videoni darsga biriktiradi va ESKI fayl nomini qaytaradi.
 *
 * Eski nom qaytariladi, o'chirilmaydi: faylni o'chirish — disk amali,
 * bu esa baza qatlami. Chaqiruvchi bazani yangilagach eski faylni
 * o'chiradi. Teskarisi bo'lsa (avval fayl) yozuv yiqilganda dars
 * videosiz qolardi. */
export function videoBiriktir(
  id: number,
  nom: string | null,
  hozir = new Date(),
): { ok: boolean; eskiNom: string | null } {
  const oldingi = dars(id);
  if (!oldingi) return { ok: false, eskiNom: null };
  db()
    .prepare(`update content set video_path = ?, updated_at = ? where id = ?`)
    .run(nom, vaqtSatri(hozir), id);
  return { ok: true, eskiNom: oldingi.videoPath === nom ? null : oldingi.videoPath };
}

// --------------------------------------------------------------------------- //
//  Ijtimoiy tarmoqlar (bosh sahifa pastida)
// --------------------------------------------------------------------------- //

/** Ruxsat etilgan ikonkalar. Ixtiyoriy matn EMAS: noma'lum qiymat kelsa
 *  sayt bo'sh joy ko'rsatardi va sabab ko'rinmasdi. */
export const IKONKALAR = ["telegram", "instagram", "youtube", "web"] as const;
export type Ikonka = (typeof IKONKALAR)[number];

export type Havola = {
  id: number;
  title: string;
  url: string;
  icon: Ikonka;
  position: number;
  active: boolean;
};

function havolagaAylantir(q: Qator): Havola {
  const icon = q.icon as string;
  return {
    id: songaAylantir(q.id),
    title: q.title as string,
    url: q.url as string,
    icon: (IKONKALAR as readonly string[]).includes(icon) ? (icon as Ikonka) : "web",
    position: songaAylantir(q.position),
    active: Boolean(q.is_active),
  };
}

/** Saytda ko'rinadigan havolalar. */
export function havolalar(): Havola[] {
  const qatorlar = db()
    .prepare(
      `select id, title, url, icon, position, is_active from social_links
        where is_active = 1 order by position asc, id asc`,
    )
    .all() as Qator[];
  return qatorlar.map(havolagaAylantir);
}

/** Admin ro'yxati — o'chirilganlari ham ko'rinadi. */
export function barchaHavolalar(): Havola[] {
  const qatorlar = db()
    .prepare(
      `select id, title, url, icon, position, is_active from social_links
        order by position asc, id asc`,
    )
    .all() as Qator[];
  return qatorlar.map(havolagaAylantir);
}

export type HavolaNatijasi = { ok: true; id: number } | { ok: false; sabab: string };

/** Havolani saqlaydi.
 *
 * URL faqat `http`/`https` bo'lishi mumkin: `javascript:` manzili
 * havolaga qo'yilsa, uni bosgan foydalanuvchining brauzerida ixtiyoriy
 * kod ishga tushardi.
 */
export function havolaSaqla(
  id: number | null,
  kirish: { title: string; url: string; icon: string; position: number; active: boolean },
  hozir = new Date(),
): HavolaNatijasi {
  const title = kirish.title.trim();
  if (!title) return { ok: false, sabab: "Nom yozilishi shart" };

  const url = kirish.url.trim();
  let tekshirilgan: URL;
  try {
    tekshirilgan = new URL(url);
  } catch {
    return { ok: false, sabab: "Havola to'liq manzil bo'lishi kerak (https://...)" };
  }
  if (tekshirilgan.protocol !== "http:" && tekshirilgan.protocol !== "https:") {
    return { ok: false, sabab: "Faqat http yoki https manzillari qabul qilinadi" };
  }

  const icon = (IKONKALAR as readonly string[]).includes(kirish.icon) ? kirish.icon : "web";
  const baza = db();
  const vaqtNow = vaqtSatri(hozir);

  if (id !== null) {
    baza
      .prepare(
        `update social_links set title = ?, url = ?, icon = ?, position = ?,
                                 is_active = ?, updated_at = ? where id = ?`,
      )
      .run(title, url, icon, kirish.position, kirish.active ? 1 : 0, vaqtNow, id);
    return { ok: true, id };
  }

  const natija = baza
    .prepare(
      `insert into social_links (title, url, icon, position, is_active, created_at, updated_at)
       values (?, ?, ?, ?, ?, ?, ?)`,
    )
    .run(title, url, icon, kirish.position, kirish.active ? 1 : 0, vaqtNow, vaqtNow);
  return { ok: true, id: songaAylantir(natija.lastInsertRowid) };
}

export function havolaOchir(id: number): boolean {
  return db().prepare(`delete from social_links where id = ?`).run(id).changes > 0;
}

// --------------------------------------------------------------------------- //
//  Jonli tahlil monitori — "oshxona ko'rinishi"
// --------------------------------------------------------------------------- //

export type JonliBosqich = {
  stage: string;
  status: "pass" | "fail" | "pending";
  reason: string | null;
};

export type JonliCoin = {
  symbol: string;
  bosqichlar: JonliBosqich[];
  score: number | null;
  /** Barcha bosqichlardan o'tdimi — kartochka yashil bo'ladi */
  signal: boolean;
};

export type JonliXulosa = {
  jami: number;
  signal: number;
  /** Eng ko'p coin to'xtagan bosqich va o'sha yerdagi soni */
  engKopBosqich: string | null;
  engKopSoni: number;
  /** Ball chegarasigacha yetganlar — ya'ni butun tahlildan o'tganlar */
  chegaraga: number;
  ortachaBall: number | null;
  engYuqoriBall: number | null;
};

export type JonliHolat = {
  cycleAt: Date | null;
  coinlar: JonliCoin[];
  /** Sikl darajasidagi to'xtash (`market_health`) — bo'lsa */
  siklToxtadi: string | null;
  /** Tepadagi bir qatorli xulosa — kartochkalarni sanab chiqmaslik uchun */
  xulosa: JonliXulosa | null;
};

/** Oxirgi siklning bosqichma-bosqich holati.
 *
 * FAQAT OXIRGI SIKL ko'rsatiladi: monitor "hozir nima bo'lyapti" degan
 * savolga javob beradi. Bir necha siklni aralashtirsak, bir coin ikki
 * marta va ikki xil natija bilan chiqardi.
 */

/** Monitor tepasidagi bir qatorli xulosa.
 *
 * NIMA UCHUN SERVERDA: mijoz tomonda hisoblansak, bir xil savolga
 * (nechta coin qayerda to'xtadi) ikki joyda javob bo'lardi — bu
 * loyihaning 1-naqshi. Kartochkalar ham, xulosa ham bitta manbadan.
 */
function xulosaHisobla(coinlar: JonliCoin[]): JonliXulosa | null {
  if (coinlar.length === 0) return null;

  const sanoq = new Map<string, number>();
  let chegaraga = 0;
  const ballar: number[] = [];

  for (const coin of coinlar) {
    if (coin.score !== null) ballar.push(coin.score);
    const yiqilgan = coin.bosqichlar.find((b) => b.status === "fail");
    if (!yiqilgan) continue;
    sanoq.set(yiqilgan.stage, (sanoq.get(yiqilgan.stage) ?? 0) + 1);
    // "Chegaraga yetdi" — butun tahlildan o'tib, faqat ball yetmagan.
    if (yiqilgan.stage === "threshold") chegaraga += 1;
  }

  let engKopBosqich: string | null = null;
  let engKopSoni = 0;
  for (const [bosqich, soni] of sanoq) {
    if (soni > engKopSoni) {
      engKopBosqich = bosqich;
      engKopSoni = soni;
    }
  }

  return {
    jami: coinlar.length,
    signal: coinlar.filter((c) => c.signal).length,
    engKopBosqich,
    engKopSoni,
    chegaraga,
    ortachaBall:
      ballar.length > 0 ? ballar.reduce((a, b) => a + b, 0) / ballar.length : null,
    engYuqoriBall: ballar.length > 0 ? Math.max(...ballar) : null,
  };
}
