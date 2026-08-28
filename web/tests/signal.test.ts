import assert from "node:assert/strict";
import { test } from "node:test";

import { bazadanNusxa } from "./nusxa.ts";

const vaqtinchalik = bazadanNusxa("hcs-sig-");
process.env.DATABASE_URL = `sqlite+aiosqlite:///${vaqtinchalik}`;

const { db } = await import("../src/lib/db.ts");
const {
  balansSaqla,
  darsOchir,
  darsSaqla,
  darslar,
  foydalanuvchiOl,
  pozitsiyaOl,
  pozitsiyaQayd,
  signalOchir,
  signalOgohlantirishlari,
  signalYarat,
  tarqatilmaganSignallar,
} = await import("../src/lib/queries.ts");
const { savdoQoidalari } = await import("../src/lib/config.ts");

const YAXSHI = { symbol: "BTC", entry: 100, stop: 97, tp1: 106, tp2: 115, note: null };

// --------------------------------------------------------------------------- //
//  Signal: symbol shakli — ASOSIY AKTIV, juftlik emas
// --------------------------------------------------------------------------- //

/** Bazada `symbol` — `DOT`, `DOTUSDT` emas: bot ham shunday yozadi
 *  (`core/halal_screening/screener.py` -> `pair_for()` juftlikni
 *  ALOHIDA yasaydi). Admin juftlikni to'liq yozib yuborsa, bitta
 *  ustunda ikki xil shakl paydo bo'lardi.
 *
 *  Bu haqiqiy xatodan keyin yozildi: grafikka `BINANCE:DOT` berilgan
 *  edi va TradingView "This symbol doesn't exist" deb turdi. */
test("juftlik yozilsa ham bazaga asosiy aktiv tushadi", () => {
  const natija = signalYarat({ ...YAXSHI, symbol: "DOTUSDT" });
  assert.ok(natija.ok);
  const qator = db()
    .prepare("select symbol from signals where id = ?")
    .get(natija.id) as { symbol: string };
  assert.equal(qator.symbol, "DOT");
});

test("asosiy aktiv yozilsa o'zgarmaydi", () => {
  const natija = signalYarat({ ...YAXSHI, symbol: "dot" });
  assert.ok(natija.ok);
  const qator = db()
    .prepare("select symbol from signals where id = ?")
    .get(natija.id) as { symbol: string };
  assert.equal(qator.symbol, "DOT");
});

// --------------------------------------------------------------------------- //
//  Signal: darajalar tartibi
// --------------------------------------------------------------------------- //

/** Bu qoidalar TA'RIF: spot (long) savdoda Stop kirishdan past, TP lar
 *  yuqori bo'lishi shart. Botdagi `SignalLevels` ham shuni tekshiradi. */
test("to'g'ri signal yoziladi va tarqatilmagan bo'lib qoladi", () => {
  const natija = signalYarat({ ...YAXSHI, note: "sinov" });
  assert.ok(natija.ok);

  const qator = db()
    .prepare("select symbol, status, broadcast_at, note, source from signals where id = ?")
    .get(natija.id) as Record<string, unknown>;
  assert.equal(qator.symbol, "BTC");
  assert.equal(qator.status, "pending");
  assert.equal(qator.source, "manual");
  assert.equal(qator.note, "sinov");
  assert.equal(
    qator.broadcast_at,
    null,
    "sayt tarqatmaydi — bot uni shu belgisiga qarab topadi",
  );
  assert.ok(tarqatilmaganSignallar().some((s) => s.id === natija.id));
});

test("Stop kirishdan past bo'lishi SHART", () => {
  for (const buzuq of [
    { ...YAXSHI, stop: 100 },
    { ...YAXSHI, stop: 105 },
  ]) {
    const n = signalYarat(buzuq);
    assert.equal(n.ok, false);
    assert.match((n as { sabab: string }).sabab, /Stop/);
  }
});

test("TP lar o'sib borishi shart", () => {
  assert.equal(signalYarat({ ...YAXSHI, tp1: 99 }).ok, false, "TP1 kirishdan yuqori bo'lsin");
  assert.equal(signalYarat({ ...YAXSHI, tp2: 105 }).ok, false, "TP2 TP1 dan yuqori bo'lsin");
});

test("manfiy va son bo'lmagan qiymatlar rad etiladi", () => {
  for (const buzuq of [
    { ...YAXSHI, entry: 0 },
    { ...YAXSHI, stop: -1 },
    { ...YAXSHI, tp2: Number.NaN },
  ]) {
    assert.equal(signalYarat(buzuq).ok, false);
  }
});

test("noto'g'ri symbol rad etiladi", () => {
  for (const yomon of ["", "B", "BTC USDT", "BTC'; drop table signals;--"]) {
    assert.equal(signalYarat({ ...YAXSHI, symbol: yomon }).ok, false, yomon);
  }
  assert.ok((db().prepare("select count(*) c from signals").get() as { c: number }).c >= 0);
});

// --------------------------------------------------------------------------- //
//  Signal: ogohlantirishlar (TAQIQ EMAS)
// --------------------------------------------------------------------------- //

/** Botda ham shunday: qo'lda kiritilgan signalda 3.3-band qoidalari
 *  majburiy emas — admin bilib turib chetga chiqishi mumkin. */
test("qoidaga sig'magan signal YOZILADI, lekin ogohlantiriladi", () => {
  const q = savdoQoidalari();
  // R/R ataylab past: TP2 juda yaqin
  const zaif = { symbol: "ETHUSDT", entry: 100, stop: 90, tp1: 104, tp2: 105, note: null };
  const natija = signalYarat(zaif);

  assert.ok(natija.ok, "yozilishi kerak");
  assert.ok(natija.ogohlantirishlar.length > 0, "ogohlantirish bo'lishi kerak");
  assert.ok(
    natija.ogohlantirishlar.some((o) => o.includes("R/R")),
    `R/R ogohlantirishi kutilgan (chegara ${q.minRiskReward}), keldi: ${natija.ogohlantirishlar}`,
  );
});

test("qoidaga to'liq mos signalda ogohlantirish yo'q", () => {
  // Stop 3%, TP1 6%, TP2 15% -> R/R 5.0
  assert.deepEqual(signalOgohlantirishlari(YAXSHI), []);
});

test("juda keng Stop ogohlantiriladi", () => {
  const q = savdoQoidalari();
  const keng = { ...YAXSHI, stop: 100 - (q.maxStopPct + 5) };
  assert.ok(signalOgohlantirishlari(keng).some((o) => o.includes("Stop masofasi")));
});

// --------------------------------------------------------------------------- //
//  Video darsliklar
// --------------------------------------------------------------------------- //

test("dars qo'shiladi, tahrirlanadi va o'chiriladi", () => {
  const yaratildi = darsSaqla(null, {
    title: "Sinov darsi",
    description: "Tavsif",
    minTier: "pro",
    position: 7,
    fileId: null,
    published: true,
  });
  assert.ok(yaratildi.ok);

  let dars = darslar().find((d) => d.id === yaratildi.id);
  assert.equal(dars?.title, "Sinov darsi");
  assert.equal(dars?.minTier, "pro");
  assert.equal(dars?.fileId, null, "video hali biriktirilmagan");

  darsSaqla(yaratildi.id, {
    title: "Yangilangan",
    description: null,
    minTier: "premium",
    position: 2,
    fileId: null,
    published: false,
  });
  dars = darslar().find((d) => d.id === yaratildi.id);
  assert.equal(dars?.title, "Yangilangan");
  assert.equal(dars?.minTier, "premium");
  assert.equal(dars?.published, false);

  assert.equal(darsOchir(yaratildi.id), true);
  assert.ok(!darslar().some((d) => d.id === yaratildi.id));
});

/** Video fayl faqat Telegram orqali biriktiriladi (`file_id`). Tahrirda
 *  bo'sh qoldirilsa, mavjud fayl YO'QOLMASLIGI kerak — aks holda
 *  sarlavhani tuzatgan admin darsni ham buzib qo'yardi. */
test("bo'sh file_id mavjud videoni o'chirmaydi", () => {
  const y = darsSaqla(null, {
    title: "Videoli dars",
    description: null,
    minTier: "pro",
    position: 1,
    fileId: "TELEGRAM_FILE_123",
    published: true,
  });
  assert.ok(y.ok);

  darsSaqla(y.id, {
    title: "Nomi o'zgardi",
    description: null,
    minTier: "pro",
    position: 1,
    fileId: null,
    published: true,
  });

  const dars = darslar().find((d) => d.id === y.id);
  assert.equal(dars?.fileId, "TELEGRAM_FILE_123", "video saqlanishi kerak");
  darsOchir(y.id);
});

test("sarlavhasiz dars rad etiladi", () => {
  const n = darsSaqla(null, {
    title: "   ",
    description: null,
    minTier: "pro",
    position: 0,
    fileId: null,
    published: true,
  });
  assert.equal(n.ok, false);
});

// --------------------------------------------------------------------------- //
//  Signalni o'chirish — bog'liq yozuvlar bilan birga
// --------------------------------------------------------------------------- //

/** NEGA BU TEST BOR: sxemada `user_positions` va `signal_events`
 *  signalga `ondelete="CASCADE"` bilan bog'langan, LEKIN SQLite'da
 *  tashqi kalitlar standart holda O'CHIQ (`PRAGMA foreign_keys = 0`).
 *  Ya'ni CASCADE ga tayanib bo'lmaydi va faqat `signals` dan
 *  o'chirilsa, foydalanuvchining pozitsiyasi mavjud bo'lmagan signalga
 *  ishora qilib qolardi — portfel va statistika buzilardi. */
test("signal o'chirilganda unga bog'liq yozuvlar ham ketadi", () => {
  const natija = signalYarat({ ...YAXSHI, symbol: "OCHIR" });
  assert.ok(natija.ok);
  const id = natija.id;

  const baza = db();
  baza
    .prepare(
      `insert into signal_events (signal_id, event, created_at, updated_at)
       values (?, 'created', datetime('now'), datetime('now'))`,
    )
    .run(id);
  baza
    .prepare(
      `insert into user_positions
         (user_id, signal_id, amount_usd, entry_price, trade_date, created_at, updated_at)
       values (1, ?, 100, 100, date('now'), datetime('now'), datetime('now'))`,
    )
    .run(id);

  const sanoq = (jadval: string) =>
    Number(
      (
        baza
          .prepare(`select count(*) as n from ${jadval} where signal_id = ?`)
          .get(id) as { n: number }
      ).n,
    );

  assert.equal(sanoq("signal_events"), 1);
  assert.equal(sanoq("user_positions"), 1);

  assert.equal(signalOchir(id), true);

  assert.equal(sanoq("signal_events"), 0, "signal_events yetim qoldi");
  assert.equal(sanoq("user_positions"), 0, "user_positions yetim qoldi");
  const qolgan = baza
    .prepare("select count(*) as n from signals where id = ?")
    .get(id) as { n: number };
  assert.equal(Number(qolgan.n), 0);
});

test("mavjud bo'lmagan signalni o'chirish false qaytaradi", () => {
  assert.equal(signalOchir(999999), false);
});

// --------------------------------------------------------------------------- //
//  "Men sotib oldim" — qoidalar BOTDAGI bilan bir xil
// --------------------------------------------------------------------------- //

/** Bu qoidalar `bot/handlers/portfolio.py` dagi `save_position` dan
 *  ko'chirilgan. Ikki joyda ikki xil bo'lsa, botda rad etilgan yozuv
 *  saytda o'tib ketardi va portfel ikki xil ma'lumot ko'rsatardi. */
test("pozitsiya qayd etiladi va portfelga tushadi", () => {
  const s = signalYarat({ ...YAXSHI, symbol: "KIRDIM" });
  assert.ok(s.ok);

  assert.deepEqual(pozitsiyaQayd(1, s.id, 250), { ok: true });
  const p = pozitsiyaOl(1, s.id);
  assert.equal(p?.amountUsd, 250);
  // Kirish narxi SIGNALDAN olinadi, foydalanuvchidan emas.
  assert.equal(p?.entryPrice, YAXSHI.entry);
});

test("bitta signalga ikki marta kirib bo'lmaydi", () => {
  const s = signalYarat({ ...YAXSHI, symbol: "IKKI" });
  assert.ok(s.ok);
  assert.deepEqual(pozitsiyaQayd(1, s.id, 100), { ok: true });

  const yana = pozitsiyaQayd(1, s.id, 500);
  assert.equal(yana.ok, false);
  // Bazadagi yozuv O'ZGARMAGAN bo'lishi kerak.
  assert.equal(pozitsiyaOl(1, s.id)?.amountUsd, 100);
});

test("yopilgan signalga kirib bo'lmaydi", () => {
  const s = signalYarat({ ...YAXSHI, symbol: "YOPIQ" });
  assert.ok(s.ok);
  db().prepare("update signals set status = 'stopped' where id = ?").run(s.id);

  const natija = pozitsiyaQayd(1, s.id, 100);
  assert.equal(natija.ok, false);
  assert.equal(pozitsiyaOl(1, s.id), null);
});

test("juda kichik yoki noto'g'ri miqdor rad etiladi", () => {
  const s = signalYarat({ ...YAXSHI, symbol: "KICHIK" });
  assert.ok(s.ok);
  for (const yomon of [0, -50, Number.NaN]) {
    assert.equal(pozitsiyaQayd(1, s.id, yomon).ok, false, `o'tkazib yubordi: ${yomon}`);
  }
  assert.equal(pozitsiyaOl(1, s.id), null);
});

test("mavjud bo'lmagan signalga kirib bo'lmaydi", () => {
  assert.equal(pozitsiyaQayd(1, 999999, 100).ok, false);
});

// --------------------------------------------------------------------------- //
//  Balans
// --------------------------------------------------------------------------- //

test("balans saqlanadi va o'chiriladi", () => {
  assert.deepEqual(balansSaqla(1, 1500), { ok: true });
  assert.equal(foydalanuvchiOl(5000001)?.declaredBalanceUsd, 1500);

  // `null` — "ko'rsatmayman", 0 dan FARQ QILADI.
  assert.deepEqual(balansSaqla(1, null), { ok: true });
  assert.equal(foydalanuvchiOl(5000001)?.declaredBalanceUsd, null);

  assert.deepEqual(balansSaqla(1, 0), { ok: true });
  assert.equal(foydalanuvchiOl(5000001)?.declaredBalanceUsd, 0);
});

test("manfiy balans rad etiladi", () => {
  assert.equal(balansSaqla(1, -100).ok, false);
});
