import { db, songaAylantir, vaqt, vaqtSatri } from "./db.ts";
import { obunaKunlari } from "./config.ts";

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
  | "cancelled";

export type Signal = {
  id: number;
  symbol: string;
  source: string;
  status: SignalHolati;
  entry: number;
  stop: number;
  tp1: number;
  tp2: number;
  entryOrderType: string;
  score: number | null;
  halalReason: string | null;
  scoreBreakdown: string | null;
  marketHealthAtEntry: number | null;
  createdAt: Date | null;
  closedAt: Date | null;
  resultPct: number | null;
};

/** Botdagi `SignalStatus.is_enterable` — TP1 olgan yoki zaiflashgan
 *  signalga endi kirish kerak emas: Stopgacha masofa o'sha-o'sha, TPgacha
 *  esa qisqargan. Yangi foydalanuvchi buni o'zi hisoblamasligi kerak. */
export function kirishMumkin(holat: SignalHolati): boolean {
  return holat === "pending" || holat === "active";
}

export function yopilgan(holat: SignalHolati): boolean {
  return holat === "tp2_hit" || holat === "stopped" || holat === "cancelled";
}

export type Salomatlik = {
  value: number;
  band: string;
  trendBreadthScore: number | null;
  btcDominanceScore: number | null;
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
    tp2: Number(q.tp2),
    entryOrderType: (q.entry_order_type as string) ?? "limit",
    score: son(q.score),
    halalReason: (q.halal_reason as string) ?? null,
    scoreBreakdown: (q.score_breakdown as string) ?? null,
    marketHealthAtEntry: son(q.market_health_at_entry),
    createdAt: vaqt(q.created_at as string),
    closedAt: vaqt(q.closed_at as string),
    resultPct: son(q.result_pct),
  };
}

const SIGNAL_USTUNLARI = `id, symbol, source, status, entry, stop, tp1, tp2,
  entry_order_type, score, halal_reason, score_breakdown,
  market_health_at_entry, created_at, closed_at, result_pct`;

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
    trendBreadthScore: son(q.trend_breadth_score),
    btcDominanceScore: son(q.btc_dominance_score),
    volatilityScore: son(q.volatility_score),
    userCapacityScore: son(q.user_capacity_score),
    saturationScore: son(q.saturation_score),
    createdAt: vaqt(q.created_at as string),
  };
}

const SALOMATLIK_USTUNLARI = `value, band, trend_breadth_score, btc_dominance_score,
  volatility_score, user_capacity_score, saturation_score, created_at`;

/** Kunlik "oldindan ko'rish" yozuvlari chiqarib tashlanadi — ular
 *  bashorat, o'lchov emas (`is_daily_preview`). */
export function salomatlikOxirgi(): Salomatlik | null {
  const q = db()
    .prepare(
      `select ${SALOMATLIK_USTUNLARI} from market_health_log
        where is_daily_preview = 0 order by created_at desc limit 1`,
    )
    .get() as Qator | undefined;
  return q ? salomatlikkaAylantir(q) : null;
}

export function salomatlikTarixi(limit = 24): Salomatlik[] {
  const qatorlar = db()
    .prepare(
      `select ${SALOMATLIK_USTUNLARI} from market_health_log
        where is_daily_preview = 0 order by created_at desc limit ?`,
    )
    .all(limit) as Qator[];
  return qatorlar.map(salomatlikkaAylantir);
}

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

export function voronka(since: Date): VoronkaQatori[] {
  const qatorlar = db()
    .prepare(
      `select reason as stage, count(*) as soni
         from risk_blocks where created_at >= ?
        group by reason order by soni desc`,
    )
    .all(vaqtSatri(since)) as Qator[];
  return qatorlar.map((q) => ({
    stage: q.stage as string,
    count: Number(q.soni),
    routine: false,
  }));
}

/** Ball chegarasida to'xtaganlarning ball statistikasi.
 *
 * Bu raqamlarsiz "chegara juda balandmi yoki nomzodlar zaifmi" degan
 * savolga javob bo'lmaydi — dashboard faqat "chegaradan past" deb
 * yozardi. Aynan shu ko'rlik sababli chegara 48 soat davomida erishib
 * bo'lmas darajada balandligi sezilmagan edi.
 */
export function ballStatistikasi(
  since: Date,
  stage = "threshold",
): { soni: number; engYuqori: number; ortacha: number } | null {
  const q = db()
    .prepare(
      `select count(*) as soni, max(score) as eng, avg(score) as ort
         from risk_blocks
        where created_at >= ? and reason = ? and score is not null`,
    )
    .get(vaqtSatri(since), stage) as Qator;
  const soni = Number(q.soni ?? 0);
  if (!soni) return null;
  return { soni, engYuqori: Number(q.eng), ortacha: Number(q.ort) };
}

// --------------------------------------------------------------------------- //
//  Kontent va narxlar
// --------------------------------------------------------------------------- //

export function kontent(): Kontent[] {
  const qatorlar = db()
    .prepare(
      `select id, kind, title, description, min_tier, position
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
              u.telegram_id, u.username, u.full_name
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
export function hisobotlar(limit = 8): Hisobot[] {
  const qatorlar = db()
    .prepare(
      `select id, generated_at, period_days, rendered, total, traded, tp2,
              tp1_then_stop, stop, cancelled, false_signals, average_score,
              average_holding_hours, pattern_count, sample_warning
         from audit_reports order by generated_at desc limit ?`,
    )
    .all(limit) as Qator[];
  return qatorlar.map((q) => ({
    id: Number(q.id),
    generatedAt: vaqt(q.generated_at as string),
    periodDays: Number(q.period_days),
    rendered: (q.rendered as string) ?? "",
    total: Number(q.total),
    traded: Number(q.traded),
    tp2: Number(q.tp2),
    tp1ThenStop: Number(q.tp1_then_stop),
    stop: Number(q.stop),
    cancelled: Number(q.cancelled),
    falseSignals: Number(q.false_signals),
    averageScore: son(q.average_score),
    averageHoldingHours: son(q.average_holding_hours),
    patternCount: Number(q.pattern_count),
    sampleWarning: (q.sample_warning as string) ?? null,
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
