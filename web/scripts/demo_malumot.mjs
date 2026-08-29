/** ISHLAB CHIQISH uchun namunaviy ma'lumot (dev seed).
 *
 * Nima uchun kerak: mahalliy baza bo'sh — sahifalarni ko'z bilan
 * tekshirib bo'lmaydi. Bu skript FAQAT `data/hcs.db` bo'sh bo'lganda
 * ishlaydi: ishlab chiqarish bazasiga tasodifan yozib yubormaslik uchun
 * foydalanuvchilar bor bo'lsa darhol to'xtaydi.
 *
 *   node scripts/demo_malumot.mjs
 */
import { DatabaseSync } from "node:sqlite";
import path from "node:path";

const yol = path.resolve(process.cwd(), "..", "data", "hcs.db");
const baza = new DatabaseSync(yol);

const bor = baza.prepare("select count(*) c from users").get().c;
if (bor > 0 && process.argv[2] !== "--majburiy") {
  console.error(
    `TO'XTATILDI: bazada ${bor} ta foydalanuvchi bor (${yol}).\n` +
      `Bu ishlab chiqarish bazasi bo'lishi mumkin. Baribir kerak bo'lsa: --majburiy`,
  );
  process.exit(1);
}

const V = (d) => d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "");
const hozir = new Date();
const oldin = (soat) => V(new Date(hozir.getTime() - soat * 3600_000));

const TG_ODDIY = 5_000_001;
const TG_ADMIN = 5_000_002;

baza.exec("begin");

for (const [tg, ism, rol] of [
  [TG_ODDIY, "Diyorbek Sinov", "user"],
  [TG_ADMIN, "Admin Sinov", "admin"],
]) {
  baza
    .prepare(
      `insert or ignore into users (telegram_id, username, full_name, role, language,
        is_blocked, declared_balance_usd, last_active_at, created_at, updated_at)
       values (?, ?, ?, ?, 'uz', 0, ?, ?, ?, ?)`,
    )
    .run(tg, ism.split(" ")[0].toLowerCase(), ism, rol, tg === TG_ODDIY ? 1500 : null,
         V(hozir), V(hozir), V(hozir));
}
const uid = (tg) => baza.prepare("select id from users where telegram_id = ?").get(tg).id;

baza
  .prepare(
    `insert into subscriptions (user_id, tier, period, status, starts_at, expires_at,
       is_trial, created_at, updated_at)
     values (?, 'pro', 'monthly', 'active', ?, ?, 0, ?, ?)`,
  )
  .run(uid(TG_ODDIY), oldin(240), V(new Date(hozir.getTime() + 18 * 86400_000)), V(hozir), V(hozir));

// --- Signallar: har bir holatdan ---
const signallar = [
  ["BTCUSDT", "active", 61250.5, 59800, 63100, 65400, 58.4, 12],
  ["ETHUSDT", "pending", 2985.2, 2890, 3080, 3210, 54.1, 6],
  ["SOLUSDT", "tp1_hit", 148.35, 142.1, 155.2, 163.0, 61.2, 40],
  ["LINKUSDT", "tp2_hit", 17.42, 16.5, 18.1, 19.05, 56.8, 96],
  ["AVAXUSDT", "stopped", 34.15, 32.6, 35.8, 37.4, 51.3, 120],
  ["ADAUSDT", "cancelled", 0.4412, 0.4210, 0.4630, 0.4880, 49.7, 150],
];
for (const [sym, holat, entry, stop, tp1, tp2, ball, soat] of signallar) {
  const yopiq = ["tp2_hit", "stopped", "cancelled"].includes(holat);
  const natija = holat === "tp2_hit" ? 9.36 : holat === "stopped" ? -4.54 : null;
  baza
    .prepare(
      `insert into signals (symbol, source, status, entry, stop, tp1, tp2,
         entry_order_type, exit_order_type, score, score_breakdown, halal_reason,
         market_health_at_entry, activated_at, closed_at, close_price, result_pct,
         is_false_signal, created_at, updated_at)
       values (?, 'classic_ta', ?, ?, ?, ?, ?, ?, 'oco', ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)`,
    )
    .run(
      sym, holat, entry, stop, tp1, tp2,
      holat === "pending" ? "limit" : "market",
      ball,
      JSON.stringify({ trend: 17.4, zona: 15.0, indikator: 11.2, hajm: 8.8, nisbat: 6.0 }),
      `${sym.replace("USDT", "")} — foizsiz (riba yo'q), asosiy faoliyati ruxsat etilgan sohada. Qimor yoki spirtli ichimlik bilan bog'liq emas.`,
      66.4,
      holat === "pending" ? null : oldin(soat),
      yopiq ? oldin(Math.max(1, soat - 20)) : null,
      yopiq ? tp2 : null,
      natija,
      oldin(soat), oldin(soat),
    );
}

// --- Pozitsiyalar ---
const sid = (sym) => baza.prepare("select id from signals where symbol = ?").get(sym).id;
for (const [sym, hajm, kirish, chiqish, pnl, pfoiz] of [
  ["BTCUSDT", 300, 61250.5, null, null, null],
  ["LINKUSDT", 250, 17.42, 19.05, 23.4, 9.36],
  ["AVAXUSDT", 200, 34.15, 32.6, -9.08, -4.54],
]) {
  baza
    .prepare(
      `insert into user_positions (user_id, signal_id, amount_usd, entry_price,
         risk_amount_usd, trade_date, closed_at, exit_price, pnl_usd, pnl_pct,
         created_at, updated_at)
       values (?, ?, ?, ?, ?, date('now'), ?, ?, ?, ?, ?, ?)`,
    )
    .run(uid(TG_ODDIY), sid(sym), hajm, kirish, hajm * 0.02,
         chiqish === null ? null : oldin(10), chiqish, pnl, pfoiz, V(hozir), V(hozir));
}

// --- Bozor Salomatligi tarixi ---
for (let i = 7; i >= 0; i -= 1) {
  const qiymat = 52 + i * 1.8 + (i % 3) * 2.4;
  baza
    .prepare(
      `insert into market_health_log (value, band, btc_dominance_score, trend_breadth_score,
         volatility_score, user_capacity_score, saturation_score,
         structure_breadth_score, quarterly_phase_score, is_daily_preview,
         created_at, updated_at)
       values (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)`,
    )
    // Omil ballari 0..1 — bot AYNAN shu shkalada yozadi
    // (`HealthFactor.score`). Ilgari bu yerda 0-100 turardi va u
    // saytdagi shkala xatosini yashirib kelgan edi.
    .run(qiymat, qiymat >= 65 ? "high" : qiymat >= 40 ? "mid" : "low",
         0.62, 0.44, 0.71, 0.88, 0.79, 0.58, 0.5, oldin(i * 4), oldin(i * 4));
}

// --- Rad etish sabablari (voronka) ---
const sabablar = [
  ["classic_ta:zone_position", 412],
  ["classic_ta:levels", 168],
  ["classic_ta:levels:stop_too_far", 61],
  ["threshold", 47],
  ["risk_engine:btc_market_filter", 18],
  ["risk_engine:correlation", 7],
  ["opening_range_scalp:window", 980],
];
for (const [sabab, soni] of sabablar) {
  const yoz = baza.prepare(
    `insert into risk_blocks (symbol, reason, detail, market_health, score,
       created_at, updated_at) values (?, ?, ?, ?, ?, ?, ?)`,
  );
  for (let i = 0; i < soni; i += 1) {
    yoz.run("BTCUSDT", sabab, null, 66.4,
            sabab === "threshold" ? 38 + (i % 17) : null, oldin(i % 24), oldin(i % 24));
  }
}

// --- Kutilayotgan to'lov (admin paneli uchun) ---
baza
  .prepare(
    `insert into payments (user_id, tier, period, amount, currency, status,
       receipt_file_id, created_at, updated_at)
     values (?, 'premium', 'monthly', 2500, 'KGS', 'pending', 'demo_file', ?, ?)`,
  )
  .run(uid(TG_ADMIN), oldin(3), oldin(3));

// --- Video darslar ---
for (const [i, [nom, izoh, tarif]] of [
  ["1-dars: Halol savdo asoslari", "Riba, garar va spot savdo nima uchun ruxsat etilgan.", "pro"],
  ["2-dars: Support va Resistance", "Zonalarni qanday topamiz va nima uchun aynan shu yerda kiramiz.", "pro"],
  ["3-dars: Risk boshqaruvi", "Pozitsiya hajmi va Stop masofasi o'rtasidagi bog'liqlik.", "premium"],
].entries()) {
  baza
    .prepare(
      `insert into content (kind, title, description, file_id, min_tier, position,
         is_published, created_at, updated_at)
       values ('video', ?, ?, 'demo', ?, ?, 1, ?, ?)`,
    )
    .run(nom, izoh, tarif, i, V(hozir), V(hozir));
}

baza.exec("commit");
console.log(`Tayyor. Sinov Telegram ID lari: oddiy=${TG_ODDIY}, admin=${TG_ADMIN}`);
