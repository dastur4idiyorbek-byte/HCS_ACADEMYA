import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import { bazadanNusxa } from "./nusxa.ts";

const vaqtinchalik = bazadanNusxa("hcs-avtopost-");
process.env.DATABASE_URL = `sqlite+aiosqlite:///${vaqtinchalik}`;

const {
  SIGNAL_MANBALARI,
  kontentPostlari,
  signalgaAloqador,
  isoHafta,
  haftaBoshi,
  otganHafta,
  haftaKodi,
  hisobotMatni,
  signalPostlari,
  haftalikHisobot,
  avtomatikPostlarniYangila,
} = await import("../src/lib/avtomatik-post.ts");
const { db, vaqtSatri } = await import("../src/lib/db.ts");
const { boshPostlar, darsSaqla, darsOchir } =
  await import("../src/lib/queries.ts");

/** Avtomatik postlar — signal va haftalik hisobot.
 *
 * Bu yerdagi eng qimmat xato TAKRORLANISH bo'lardi: bosh sahifa har
 * ochilganda yangi post yozilib, oqim bir xil xabar bilan to'lib
 * ketardi. Shuning uchun testlarning yarmi aynan "ikkinchi marta
 * chaqirilganda hech narsa yozilmasin" ni tekshiradi.
 */

// --------------------------------------------------------------------------- //
//  Sof yordamchilar
// --------------------------------------------------------------------------- //

/** ISO hafta chegaralari — eng adashtiradigan joyi yil almashuvi. */
test("ISO hafta raqami — chegaradagi sanalar", () => {
  // 2026-01-01 payshanba -> 2026-yilning 1-haftasi
  assert.deepEqual(isoHafta(new Date("2026-01-01T12:00:00Z")), {
    yil: 2026,
    hafta: 1,
  });
  // 2025-12-29 dushanba -> allaqachon 2026-yilning 1-haftasi
  assert.deepEqual(isoHafta(new Date("2025-12-29T00:00:00Z")), {
    yil: 2026,
    hafta: 1,
  });
  // 2026-01-05 dushanba -> 2-hafta
  assert.deepEqual(isoHafta(new Date("2026-01-05T00:00:00Z")), {
    yil: 2026,
    hafta: 2,
  });
});

test("hafta boshi — doim dushanba, 00:00 UTC", () => {
  // Yakshanba ham O'SHA haftaga tegishli (ISO: dushanba–yakshanba)
  const yakshanba = haftaBoshi(new Date("2026-09-13T23:59:00Z"));
  assert.equal(yakshanba.toISOString(), "2026-09-07T00:00:00.000Z");
  const dushanba = haftaBoshi(new Date("2026-09-07T00:00:00Z"));
  assert.equal(dushanba.toISOString(), "2026-09-07T00:00:00.000Z");
});

test("o'tgan hafta — joriy hafta hisobga OLINMAYDI", () => {
  // Chorshanba, 2026-09-09. O'tgan hafta: 31.08 – 07.09
  const n = otganHafta(new Date("2026-09-09T10:00:00Z"));
  assert.equal(n.boshi.toISOString(), "2026-08-31T00:00:00.000Z");
  assert.equal(n.oxiri.toISOString(), "2026-09-07T00:00:00.000Z");
  assert.equal(n.yil, 2026);
});

/** Kod `yil * 100 + hafta`. U faqat hafta 100 dan kichik bo'lgani
 *  uchun to'g'ri ishlaydi — ISO da eng ko'pi 53. Chegaradagi juftlik:
 *  o'tgan yilning 53-haftasi va yangi yilning 1-haftasi. */
test("hafta kodi takrorlanmaydi", () => {
  assert.equal(haftaKodi(2026, 36), 202636);
  assert.notEqual(haftaKodi(2025, 53), haftaKodi(2026, 1));
  const kodlar = new Set<number>();
  for (let yil = 2024; yil <= 2035; yil += 1) {
    for (let hafta = 1; hafta <= 53; hafta += 1)
      kodlar.add(haftaKodi(yil, hafta));
  }
  assert.equal(kodlar.size, 12 * 53, "ikki hafta bitta kodga tushdi");
});

test("hisobot matnida faqat o'lchangan raqamlar bor", () => {
  const matn = hisobotMatni(2026, 36, {
    jami: 5,
    tp2: 3,
    tp1Keyin: 1,
    stop: 1,
    bekor: 0,
    ortacha: 2.345,
    ortachaSoni: 5,
  });
  assert.match(matn, /36-hafta/);
  assert.match(matn, /Yopilgan signallar: 5/);
  assert.match(matn, /\+2\.35%/);
  // Bekor qilingani yo'q — qatori ham chiqmasin
  assert.doesNotMatch(matn, /Bekor/);
  // "G'alaba foizi" kabi yig'ma ko'rsatkich ATAYLAB yo'q
  assert.doesNotMatch(matn, /foiz(i)?:/i);
});

test("o'rtacha o'lchanmagan bo'lsa, qatori umuman yo'q", () => {
  const matn = hisobotMatni(2026, 36, {
    jami: 2,
    tp2: 0,
    tp1Keyin: 0,
    stop: 2,
    bekor: 0,
    ortacha: null,
    ortachaSoni: 0,
  });
  assert.doesNotMatch(matn, /O'rtacha/);
});

// --------------------------------------------------------------------------- //
//  Bazaga tegadigan qism
// --------------------------------------------------------------------------- //

const HOZIR = new Date("2026-09-09T10:00:00Z");

/** Sinov signali. `broadcast` — obunachilarga yuborilganmi. */
function signalQos(k: {
  broadcast: Date | null;
  status?: string;
  closed?: Date | null;
  natija?: number | null;
  tp1?: boolean;
}): number {
  const v = vaqtSatri(HOZIR);
  const n = db()
    .prepare(
      `insert into signals
         (symbol, source, status, entry, stop, tp1, tp2, entry_order_type,
          exit_order_type, is_false_signal, tp1_reached, reached_tps,
          broadcast_at, closed_at, result_pct, created_at, updated_at)
       values ('TEST', 'manual', ?, 100, 95, 105, 110, 'limit', 'oco',
               0, ?, 0, ?, ?, ?, ?, ?)`,
    )
    .run(
      k.status ?? "active",
      k.tp1 ? 1 : 0,
      k.broadcast ? vaqtSatri(k.broadcast) : null,
      k.closed ? vaqtSatri(k.closed) : null,
      k.natija ?? null,
      v,
      v,
    );
  return Number(n.lastInsertRowid);
}

/** Signal hodisasi — aniq VAQT shu jadvaldan olinadi. */
function hodisaQos(signalId: number, hodisa: string, vaqt: Date) {
  const v = vaqtSatri(vaqt);
  db()
    .prepare(
      `insert into signal_events (signal_id, event, price, created_at, updated_at)
       values (?, ?, 100, ?, ?)`,
    )
    .run(signalId, hodisa, v, v);
}

function tozala() {
  db().exec(
    `delete from signal_events where signal_id in
       (select id from signals where symbol = 'TEST')`,
  );
  db().exec(
    `delete from homepage_posts
      where source_kind in ('signal','tp1','tp2','hisobot')`,
  );
  db().exec(`delete from signals where symbol = 'TEST'`);
  db().exec(
    `delete from homepage_posts where source_kind in ('dars','maqola')`,
  );
}

test("tarqatilgan signal uchun post yoziladi — bir marta", () => {
  tozala();
  const id = signalQos({ broadcast: new Date("2026-09-09T09:00:00Z") });

  assert.equal(signalPostlari(HOZIR), 1);
  // IKKINCHI chaqiruv hech narsa yozmasligi SHART
  assert.equal(signalPostlari(HOZIR), 0);

  const post = boshPostlar(50).find(
    (p) => p.manbaTuri === "signal" && p.manbaId === id,
  );
  assert.ok(post, "signal posti topilmadi");
  assert.equal(post.havola, `/signallar/${id}`);
  tozala();
});

/** ENG MUHIM QOIDA: tarqatilmagan signal ochiq oqimga CHIQMAYDI.
 *  Aks holda pul to'lamagan odam to'laganidan oldin bilib olardi. */
test("tarqatilmagan signal uchun post YOZILMAYDI", () => {
  tozala();
  signalQos({ broadcast: null });
  assert.equal(signalPostlari(HOZIR), 0);
  tozala();
});

test("eski signal oqimni to'ldirmaydi (uch kunlik oyna)", () => {
  tozala();
  signalQos({ broadcast: new Date("2026-08-01T09:00:00Z") });
  assert.equal(signalPostlari(HOZIR), 0);
  tozala();
});

test("post matnida coin nomi YO'Q", () => {
  tozala();
  const id = signalQos({ broadcast: new Date("2026-09-09T09:00:00Z") });
  signalPostlari(HOZIR);
  const post = boshPostlar(50).find(
    (p) => p.manbaTuri === "signal" && p.manbaId === id,
  );
  assert.ok(post);
  assert.doesNotMatch(post.matn ?? "", /TEST/);
  tozala();
});

test("haftalik hisobot — o'tgan haftaning yopilgan signallaridan", () => {
  tozala();
  // O'tgan hafta: 31.08 – 07.09
  signalQos({
    broadcast: null,
    status: "tp2_hit",
    closed: new Date("2026-09-02T10:00:00Z"),
    natija: 6,
  });
  signalQos({
    broadcast: null,
    status: "stopped",
    closed: new Date("2026-09-03T10:00:00Z"),
    natija: -2,
    tp1: true,
  });
  // JORIY haftada yopilgan — hisobga KIRMASLIGI kerak
  signalQos({
    broadcast: null,
    status: "stopped",
    closed: new Date("2026-09-08T10:00:00Z"),
    natija: -3,
  });

  assert.equal(haftalikHisobot(HOZIR), true);
  assert.equal(haftalikHisobot(HOZIR), false, "hisobot ikki marta yozildi");

  const post = boshPostlar(50).find((p) => p.manbaTuri === "hisobot");
  assert.ok(post);
  assert.match(post.matn ?? "", /Yopilgan signallar: 2/);
  assert.match(post.matn ?? "", /Nishonga yetdi \(TP2\): 1/);
  assert.match(post.matn ?? "", /TP1 dan keyin stop: 1/);
  assert.equal(post.havola, "/statistika");
  tozala();
});

test("signalsiz hafta uchun hisobot YOZILMAYDI", () => {
  tozala();
  assert.equal(haftalikHisobot(HOZIR), false);
  tozala();
});

test("yig'uvchi chaqiruv xato otmaydi", () => {
  tozala();
  const natija = avtomatikPostlarniYangila(HOZIR);
  assert.equal(typeof natija.signal, "number");
  assert.equal(typeof natija.hisobot, "boolean");
  tozala();
});

// --------------------------------------------------------------------------- //
//  TP hodisalari — "nishonga yetdi" postlari
// --------------------------------------------------------------------------- //

test("TP1 va yakuniy nishon uchun alohida post yoziladi", () => {
  tozala();
  const id = signalQos({
    broadcast: new Date("2026-09-08T09:00:00Z"),
    status: "tp2_hit",
    closed: new Date("2026-09-09T08:00:00Z"),
    natija: 6,
    tp1: true,
  });
  hodisaQos(id, "tp1_hit", new Date("2026-09-09T07:00:00Z"));
  hodisaQos(id, "tp2_hit", new Date("2026-09-09T08:00:00Z"));

  // Uchtasi: yangi signal + TP1 + yakuniy nishon
  assert.equal(signalPostlari(HOZIR), 3);
  assert.equal(signalPostlari(HOZIR), 0, "postlar takrorlandi");

  const turlari = boshPostlar(50)
    .filter((p) => p.manbaId === id)
    .map((p) => p.manbaTuri)
    .sort();
  assert.deepEqual(turlari, ["signal", "tp1", "tp2"]);
  tozala();
});

/** Hech kimga yuborilmagan signalning natijasi bilan maqtanish
 *  ma'nosiz — va u obunachilar ko'rmagan savdo bo'lardi. */
test("tarqatilmagan signalning TP si ham e'lon qilinmaydi", () => {
  tozala();
  const id = signalQos({
    broadcast: null,
    status: "tp2_hit",
    closed: new Date("2026-09-09T08:00:00Z"),
    tp1: true,
  });
  hodisaQos(id, "tp1_hit", new Date("2026-09-09T07:00:00Z"));
  assert.equal(signalPostlari(HOZIR), 0);
  tozala();
});

/** Hodisa VAQTI audit izidan olinadi, `updated_at` dan emas. Aks
 *  holda bir hafta oldin TP1 ga tekkan signal bugun TP2 ga tekkanda
 *  "TP1 hozir bo'ldi" degan post chiqardi. */
test("eski TP hodisasi uchun post yozilmaydi", () => {
  tozala();
  const id = signalQos({
    broadcast: new Date("2026-09-08T09:00:00Z"),
    status: "tp2_hit",
    closed: new Date("2026-09-09T08:00:00Z"),
    tp1: true,
  });
  hodisaQos(id, "tp1_hit", new Date("2026-08-20T07:00:00Z")); // ancha oldin
  hodisaQos(id, "tp2_hit", new Date("2026-09-09T08:00:00Z"));

  signalPostlari(HOZIR);
  const turlari = boshPostlar(50)
    .filter((p) => p.manbaId === id)
    .map((p) => p.manbaTuri)
    .sort();
  assert.deepEqual(turlari, ["signal", "tp2"], "eski TP1 posti yozilib qoldi");
  tozala();
});

test("TP postlarida ham coin nomi YO'Q", () => {
  tozala();
  const id = signalQos({
    broadcast: new Date("2026-09-08T09:00:00Z"),
    status: "tp2_hit",
    closed: new Date("2026-09-09T08:00:00Z"),
    tp1: true,
  });
  hodisaQos(id, "tp1_hit", new Date("2026-09-09T07:00:00Z"));
  hodisaQos(id, "tp2_hit", new Date("2026-09-09T08:00:00Z"));
  signalPostlari(HOZIR);

  for (const p of boshPostlar(50).filter((x) => x.manbaId === id)) {
    assert.doesNotMatch(
      p.matn ?? "",
      /TEST/,
      `${p.manbaTuri} da coin nomi bor`,
    );
  }
  tozala();
});

// --------------------------------------------------------------------------- //
//  Qulf
// --------------------------------------------------------------------------- //

test("signalga aloqador turlar qulflangan deb belgilanadi", () => {
  for (const m of SIGNAL_MANBALARI) assert.equal(signalgaAloqador(m), true);
  for (const m of ["qolda", "dars", "maqola", "hisobot"]) {
    assert.equal(signalgaAloqador(m), false, `${m} noto'g'ri qulflandi`);
  }
});

/** Har bir qulflangan turning O'Z belgisi bo'lsin.
 *
 * Ro'yxatga qo'shilib, chizuvchida unutilsa, post belgisiz chiqardi
 * va uning signalga aloqadorligi ko'rinmasdi. */
test("har bir signal turining belgisi bor", () => {
  const chizuvchi = readFileSync(
    path.join(
      import.meta.dirname,
      "..",
      "src",
      "app",
      "(ichki)",
      "bosh",
      "page.tsx",
    ),
    "utf8",
  );
  for (const m of SIGNAL_MANBALARI) {
    assert.match(chizuvchi, new RegExp(`\\n\\s*${m}: "`), `${m} belgisi yo'q`);
  }
});

// --------------------------------------------------------------------------- //
//  Dars va maqola
// --------------------------------------------------------------------------- //

const DARS = {
  kind: "video" as const,
  description: null,
  minTier: "pro" as const,
  position: 0,
  fileId: null,
  published: true,
};

test("chop etilgan dars va maqola uchun post yoziladi", () => {
  tozala();
  const dars = darsSaqla(null, { ...DARS, title: "Sinov darsi" }, HOZIR);
  const maqola = darsSaqla(
    null,
    {
      ...DARS,
      kind: "maqola",
      title: "Sinov maqolasi",
      matn: "Uzun matn.",
      toifa: "Risk",
      davomiylik: 300,
    },
    HOZIR,
  );
  assert.equal(dars.ok && maqola.ok, true);
  if (!dars.ok || !maqola.ok) return;

  assert.equal(kontentPostlari(HOZIR), 2);
  assert.equal(kontentPostlari(HOZIR), 0, "postlar takrorlandi");

  const royxat = boshPostlar(50);
  const d = royxat.find((p) => p.manbaTuri === "dars" && p.manbaId === dars.id);
  const m = royxat.find(
    (p) => p.manbaTuri === "maqola" && p.manbaId === maqola.id,
  );
  assert.ok(d, "dars posti yo'q");
  assert.ok(m, "maqola posti yo'q");
  // Dars nomi "sotiladigan qiymat" — u ochiq turadi (signaldan farqi)
  assert.equal(d.matn, "Sinov darsi");
  assert.equal(d.havola, "/video");
  // Maqola O'Z sahifasiga ochiladi
  assert.equal(m.havola, `/bilimlar/${maqola.id}`);

  darsOchir(dars.id!);
  darsOchir(maqola.id!);
  tozala();
});

/** Chop etilmagan dars hali tayyor emas — e'lon qilish erta. */
test("chop etilmagan dars uchun post YOZILMAYDI", () => {
  tozala();
  const n = darsSaqla(
    null,
    { ...DARS, title: "Tayyor emas", published: false },
    HOZIR,
  );
  assert.equal(n.ok, true);
  assert.equal(kontentPostlari(HOZIR), 0);
  if (n.ok) darsOchir(n.id!);
  tozala();
});

test("eski dars oqimni to'ldirmaydi", () => {
  tozala();
  const n = darsSaqla(
    null,
    { ...DARS, title: "Eski dars" },
    new Date("2026-08-01T10:00:00Z"),
  );
  assert.equal(n.ok, true);
  assert.equal(kontentPostlari(HOZIR), 0);
  if (n.ok) darsOchir(n.id!);
  tozala();
});

/** Bo'sh maqola — "Bilimlar" da sarlavha ko'rinadi, ochilganda esa
 *  bo'sh sahifa chiqadi va buni faqat o'quvchi sezadi. */
test("matnsiz maqola saqlanmaydi", () => {
  const n = darsSaqla(
    null,
    { ...DARS, kind: "maqola", title: "Bo'sh maqola" },
    HOZIR,
  );
  assert.equal(n.ok, false);
});
