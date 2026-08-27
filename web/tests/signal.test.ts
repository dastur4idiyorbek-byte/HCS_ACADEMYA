import assert from "node:assert/strict";
import { test } from "node:test";

import { bazadanNusxa } from "./nusxa.ts";

const vaqtinchalik = bazadanNusxa("hcs-sig-");
process.env.DATABASE_URL = `sqlite+aiosqlite:///${vaqtinchalik}`;

const { db } = await import("../src/lib/db.ts");
const {
  darsOchir,
  darsSaqla,
  darslar,
  signalOgohlantirishlari,
  signalYarat,
  tarqatilmaganSignallar,
} = await import("../src/lib/queries.ts");
const { savdoQoidalari } = await import("../src/lib/config.ts");

const YAXSHI = { symbol: "BTCUSDT", entry: 100, stop: 97, tp1: 106, tp2: 115, note: null };

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
  assert.equal(qator.symbol, "BTCUSDT");
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
