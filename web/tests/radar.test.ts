import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import {
  BUTUN_KALITLAR,
  type KalibrQator,
  SOZLAMA_KALITLARI,
  SOZLAMA_ORALIQLARI,
  SOZLAMA_STANDART,
  type SessiyaQisqa,
  type Tekshiruv,
  type YengilNatija,
  boshlanishdanKeyin,
  bugungiKun,
  joriyBolimlar,
  joriyKun,
  kalibrovka,
  keyingiSessiyalar,
  kunUstunlari,
  kunVaTartib,
  kunYaroqli,
  kunlarQatori,
  kunlikOrinlar,
  manbalarniOqi,
  mintaqaCheklanganmi,
  oylikBump,
  oynaKunlari,
  sessiyaBump,
  sessiyaJadvali,
  sessiyaUstunlari,
  seriyaUslubi,
  soatYoz,
  sonniOqi,
  sozlamaJsonOqi,
  sozlamaTekshir,
  symbolNormalla,
  tasdiqVaqti,
  tekshiruvSababi,
  tekshiruvlarniOqi,
  vaqtQismlari,
  yashirishGacha,
  zonaSanasi,
  zonaniTekshir,
  type Natija,
} from "../src/lib/radar.ts";

/** Modul 4.0.0 — sayt tomonidagi sof mantiq (`docs/MODUL_4_0_0.md`).
 *
 * Eng nozik joy — VAQT: kun 23:45 UTC da almashadi, Bishkekda esa
 * 05:45 da boshlanib 01:45 da tugaydi. Bu chegara noto'g'ri bo'lsa,
 * grafikdagi nuqta boshqa kunga tushadi va jadvaldagi foiz noto'g'ri
 * sessiyadan hisoblanadi — va hech kim buni darrov sezmaydi.
 *
 * Oxirida — QAT'IY CHEGARA testlari: modul signal bermaydi, har server
 * amali adminlikni qayta tekshiradi, sof fayl bazaga tegmaydi.
 */

const Z = (s: string) => new Date(s);
const iso = (d: Date) => d.toISOString().replace(".000Z", "Z");

// --------------------------------------------------------------------------- //
//  Vaqt jadvali
// --------------------------------------------------------------------------- //

test("keyingi A va B — oddiy holat (22:30 UTC)", () => {
  const k = keyingiSessiyalar(Z("2026-10-14T22:30:00Z"));
  assert.equal(iso(k.kashfiyot), "2026-10-14T23:00:00Z");
  assert.equal(iso(k.tasdiq), "2026-10-14T23:45:00Z");
});

test("keyingi sessiya QAT'IY kelajakda — Python `keyingisi()` bilan bir xil", () => {
  // Aynan 23:00 da A allaqachon "hozir" — keyingisi 03:00.
  let k = keyingiSessiyalar(Z("2026-10-14T23:00:00Z"));
  assert.equal(iso(k.kashfiyot), "2026-10-15T03:00:00Z");
  assert.equal(iso(k.tasdiq), "2026-10-14T23:45:00Z");

  // 23:45 — B boshlandi, keyingisi ertangi 03:45.
  k = keyingiSessiyalar(Z("2026-10-14T23:45:00Z"));
  assert.equal(iso(k.tasdiq), "2026-10-15T03:45:00Z");
  assert.equal(iso(k.kashfiyot), "2026-10-15T03:00:00Z");

  // 23:44:59 — B hali oldinda.
  k = keyingiSessiyalar(Z("2026-10-14T23:44:59Z"));
  assert.equal(iso(k.tasdiq), "2026-10-14T23:45:00Z");
});

test("oy va yil almashuvi", () => {
  assert.equal(iso(keyingiSessiyalar(Z("2026-10-31T23:50:00Z")).tasdiq), "2026-11-01T03:45:00Z");
  assert.equal(bugungiKun(Z("2026-10-31T23:50:00Z")), "2026-11-01");
  assert.equal(bugungiKun(Z("2026-12-31T23:46:00Z")), "2027-01-01");
  assert.equal(bugungiKun(Z("2026-12-31T23:44:00Z")), "2027-01-01");
  assert.equal(bugungiKun(Z("2026-12-31T19:40:00Z")), "2026-12-31");
});

test("YAML dan boshqa daqiqalar kelsa jadval ham o'zgaradi", () => {
  const j = { kashfiyotDaqiqa: 30, tasdiqDaqiqa: 5, tasdiqKechikishDaqiqa: 4 };
  const k = keyingiSessiyalar(Z("2026-10-14T03:40:00Z"), j);
  assert.equal(iso(k.kashfiyot), "2026-10-14T07:30:00Z");
  assert.equal(iso(k.tasdiq), "2026-10-14T03:55:00Z");
  assert.equal(iso(tasdiqVaqti("2026-10-14", 2, j)), "2026-10-14T03:55:00Z");
});

test("kun va tartib — shamning UTC sanasi", () => {
  assert.deepEqual(kunVaTartib(Z("2026-10-15T00:00:00Z")), { kun: "2026-10-15", tartib: 1 });
  assert.deepEqual(kunVaTartib(Z("2026-10-15T12:00:00Z")), { kun: "2026-10-15", tartib: 4 });
  assert.deepEqual(kunVaTartib(Z("2026-10-15T20:00:00Z")), { kun: "2026-10-15", tartib: 6 });
  // 23:45 UTC dagi B — KEYINGI kunning 1-sessiyasi.
  assert.equal(iso(tasdiqVaqti("2026-10-15", 1)), "2026-10-14T23:45:00Z");
});

test("Bishkekda B sessiyalari 05:45 ... 01:45, hammasi bitta kunda", () => {
  const soatlar = [1, 2, 3, 4, 5, 6].map((n) => soatYoz(tasdiqVaqti("2026-10-14", n), "Asia/Bishkek"));
  assert.deepEqual(soatlar, ["05:45", "09:45", "13:45", "17:45", "21:45", "01:45"]);
  // 6-sessiya kalendar bo'yicha keyingi kunda, lekin `kun` o'sha.
  assert.equal(zonaSanasi(tasdiqVaqti("2026-10-14", 1), "Asia/Bishkek"), "2026-10-14");
  assert.equal(zonaSanasi(tasdiqVaqti("2026-10-14", 6), "Asia/Bishkek"), "2026-10-15");
});

test("zona Intl orqali; noto'g'ri zona standartga qaytadi", () => {
  assert.equal(zonaniTekshir("Mars/Olympus"), "Asia/Bishkek");
  assert.equal(zonaniTekshir(undefined), "Asia/Bishkek");
  assert.equal(zonaniTekshir("UTC"), "UTC");
  const q = vaqtQismlari(Z("2026-10-14T18:30:00Z"), "Asia/Bishkek");
  assert.deepEqual(q, { yil: 2026, oy: 10, kun: 15, soat: 0, daqiqa: 30 });
});

test("joriy kun: oxirgi tugagan B kuni, bo'lmasa keyingi B kuni", () => {
  const hozir = Z("2026-10-14T21:00:00Z"); // 6-sessiyadan keyin
  assert.equal(joriyKun("2026-10-14", hozir), "2026-10-14");
  assert.equal(joriyKun(null, hozir), "2026-10-15");
  assert.equal(joriyKun("buzuq", hozir), "2026-10-15");
});

test("kunlar qatori va oyna", () => {
  const q = kunlarQatori("2026-10-14");
  assert.equal(q.length, 30);
  assert.equal(q[0], "2026-10-14");
  assert.equal(q[29], "2026-09-15");
  assert.deepEqual(oynaKunlari("2026-03-01", "3k"), ["2026-02-27", "2026-02-28", "2026-03-01"]);
  assert.equal(oynaKunlari("2026-10-14", "1o").length, 30);
  assert.ok(kunYaroqli("2026-02-28"));
  assert.ok(!kunYaroqli("2026-02-31"));
  assert.ok(!kunYaroqli("2026-1-01"));
  assert.ok(!kunYaroqli("'; drop table x; --"));
});

// --------------------------------------------------------------------------- //
//  Ustunlar
// --------------------------------------------------------------------------- //

const KUN = "2026-10-14";
const s = (id: number, kun: string, tartib: number, holat = "tugadi"): SessiyaQisqa => ({
  id,
  kun,
  tartib,
  holat,
});

test("ustunlar: tugagan, o'tkazib yuborilgan, kelajak va yurmoqda", () => {
  // 4-sessiyadan 30 daqiqa keyin: 5- va 6- hali kelmagan.
  const hozir = new Date(tasdiqVaqti(KUN, 4).getTime() + 30 * 60_000);
  const u = sessiyaUstunlari([KUN], [s(11, KUN, 1), s(12, KUN, 2), s(14, KUN, 4)], hozir);
  assert.deepEqual(
    u.map((x) => [x.tartib, x.holat, x.sessiyaId]),
    [
      [1, "bor", 11],
      [2, "bor", 12],
      [3, "otkazildi", null],
      [4, "bor", 14],
    ],
  );

  // Kechikish muddati ichida (14 daqiqa) natija yo'q — hali kutilmoqda.
  const yaqin = new Date(tasdiqVaqti(KUN, 5).getTime() + 5 * 60_000);
  assert.equal(sessiyaUstunlari([KUN], [], yaqin).length, 4); // 1..4 o'tkazildi, 5 yo'q

  // Yurmoqda — ustun yo'q; osilib qolgan (1 soatdan ko'p) — o'tkazildi.
  const y1 = sessiyaUstunlari([KUN], [s(15, KUN, 5, "yurmoqda")], yaqin);
  assert.equal(y1.find((x) => x.tartib === 5), undefined);
  const kech = new Date(tasdiqVaqti(KUN, 5).getTime() + 70 * 60_000);
  const y2 = sessiyaUstunlari([KUN], [s(15, KUN, 5, "yurmoqda")], kech);
  assert.equal(y2.find((x) => x.tartib === 5)?.holat, "otkazildi");

  // Xato bilan tugagan — o'tkazildi; bir slotda ikki yozuv — eng yangisi.
  const y3 = sessiyaUstunlari(
    [KUN],
    [s(20, KUN, 1, "xato"), s(21, KUN, 2), s(22, KUN, 2)],
    kech,
  );
  assert.equal(y3[0].holat, "otkazildi");
  assert.equal(y3[1].sessiyaId, 22);
});

test("oylik ustunlar: har kun bitta, sessiyasiz o'tgan kun bo'sh", () => {
  const hozir = Z("2026-10-14T12:00:00Z");
  const u = kunUstunlari(["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"], [s(1, "2026-10-12", 3)], hozir);
  assert.deepEqual(
    u.map((x) => [x.kun, x.holat]),
    [
      ["2026-10-12", "bor"],
      ["2026-10-13", "otkazildi"],
      ["2026-10-14", "otkazildi"],
    ],
  );
});

test("radar boshlanishidan oldingi ustunlar 'o'tkazib yuborildi' emas", () => {
  const hozir = Z("2026-10-15T12:00:00Z");
  const kunlar = ["2026-10-13", "2026-10-14", "2026-10-15"];
  const sessiyalar = [s(1, "2026-10-14", 3), s(2, "2026-10-15", 1)];
  const u = boshlanishdanKeyin(sessiyaUstunlari(kunlar, sessiyalar, hozir), { kun: "2026-10-14", tartib: 3 });
  assert.deepEqual(
    u.map((x) => x.kalit),
    // 12:00 da 4-sessiyaning (11:45) 14 daqiqalik muddati ham o'tgan.
    ["2026-10-14#3", "2026-10-14#4", "2026-10-14#5", "2026-10-14#6", "2026-10-15#1", "2026-10-15#2", "2026-10-15#3", "2026-10-15#4"],
  );
  const oy = boshlanishdanKeyin(kunUstunlari(kunlar, sessiyalar, hozir), { kun: "2026-10-14", tartib: 3 });
  assert.deepEqual(oy.map((x) => [x.kun, x.holat]), [["2026-10-14", "bor"], ["2026-10-15", "bor"]]);
  assert.deepEqual(boshlanishdanKeyin(u, null), []);
});

// --------------------------------------------------------------------------- //
//  Grafik — bump
// --------------------------------------------------------------------------- //

const n = (
  sessiyaId: number,
  symbol: string,
  turi: string,
  orin: number | null,
  narx: number | null = null,
  holat: YengilNatija["holat"] = "oddiy",
): YengilNatija => ({ sessiyaId, symbol, belgi: symbol, turi, orin, narx, holat });

test("bump: o'rin, Top-N dan tashqari, chiqdi va uzilish", () => {
  const hozir = new Date(tasdiqVaqti(KUN, 4).getTime() + 30 * 60_000);
  const ustunlar = sessiyaUstunlari([KUN], [s(11, KUN, 1), s(12, KUN, 2), s(14, KUN, 4)], hozir);
  const natijalar = [
    n(11, "AAA", "elak", 1),
    n(12, "AAA", "elak", 5),
    n(11, "DDD", "elak", 2),
    n(12, "DDD", "elak", 1),
    n(14, "DDD", "elak", 1),
    n(12, "BBB", "elak", 2),
    n(14, "BBB", "chiqdi", null),
    n(11, "CCC", "elak", 4), // Top-3 ga hech kirmagan — chizilmaydi
    n(12, "CCC", "elak", 6),
    n(11, "EEE", "namuna", null), // nazorat guruhi — o'rin yo'q
  ];
  const seriyalar = sessiyaBump(ustunlar, natijalar, 3);
  assert.deepEqual(
    seriyalar.map((x) => x.symbol),
    ["AAA", "DDD", "BBB"],
  );
  const nuqta = (sym: string) => seriyalar.find((x) => x.symbol === sym)!.nuqtalar;
  assert.deepEqual(nuqta("AAA"), [
    { tur: "orin", orin: 1 },
    { tur: "tashqarida", orin: 5 },
    { tur: "bosh" },
    // Oldingi MAVJUD sessiyada bor edi, endi yo'q — chiqdi.
    { tur: "chiqdi" },
  ]);
  assert.deepEqual(nuqta("DDD"), [
    { tur: "orin", orin: 2 },
    { tur: "orin", orin: 1 },
    { tur: "bosh" },
    { tur: "orin", orin: 1 },
  ]);
  // Oynada hali paydo bo'lmagan coin "chiqdi" dan boshlanmaydi.
  assert.deepEqual(nuqta("BBB"), [
    { tur: "yoq" },
    { tur: "orin", orin: 2 },
    { tur: "bosh" },
    { tur: "chiqdi" },
  ]);
  assert.deepEqual(
    seriyalar.map((x) => x.tartib),
    [0, 1, 2],
  );
});

test("bump: chiqgandan keyin qaytmagan coin keyingi ustunlarda chizilmaydi", () => {
  const hozir = Z("2026-10-14T23:00:00Z");
  const ustunlar = sessiyaUstunlari([KUN], [1, 2, 3, 4].map((t) => s(t, KUN, t)), hozir);
  const seriya = sessiyaBump(ustunlar, [n(1, "AAA", "elak", 1)], 10)[0];
  assert.deepEqual(
    seriya.nuqtalar.map((x) => x.tur),
    ["orin", "chiqdi", "yoq", "yoq", "bosh", "bosh"],
  );
});

test("rang tartib bo'yicha, 8 dan keyin chiziq shakli o'zgaradi", () => {
  assert.equal(seriyaUslubi(0).chiziq, undefined);
  assert.equal(seriyaUslubi(8).rang, seriyaUslubi(0).rang);
  assert.notEqual(seriyaUslubi(8).chiziq, seriyaUslubi(0).chiziq);
});

// --------------------------------------------------------------------------- //
//  Oylik agregat (B-variant)
// --------------------------------------------------------------------------- //

test("kunlik o'rin: Top-N da ko'p turgan, keyin o'rtacha o'rin, keyin symbol", () => {
  const qatorlar = [
    ...[1, 2, 9].map((o) => ({ symbol: "X", turi: "elak", orin: o })),
    ...[3, 1, 8].map((o) => ({ symbol: "Y", turi: "elak", orin: o })),
    ...[2, 3, 2].map((o) => ({ symbol: "Z", turi: "elak", orin: o })),
    ...[5, 4, 6].map((o) => ({ symbol: "W", turi: "elak", orin: o })),
    { symbol: "V", turi: "elak", orin: 7 },
    ...[2, 1, 10].map((o) => ({ symbol: "Q", turi: "elak", orin: o })),
    { symbol: "N", turi: "namuna", orin: null },
    { symbol: "C", turi: "chiqdi", orin: null },
  ];
  const tartib = [...kunlikOrinlar(qatorlar, 3).entries()];
  assert.deepEqual(tartib, [
    ["Z", 1], // 3 marta Top-3 da
    ["Q", 2], // 2 marta, o'rtacha 1.5 — X bilan teng, symbol bo'yicha oldin
    ["X", 3],
    ["Y", 4], // 2 marta, o'rtacha 2
    ["W", 5], // Top-3 da hech, o'rtacha 5
    ["V", 6],
  ]);
});

test("oylik bump: kunlik o'rin bilan, tashqarida va chiqdi", () => {
  const hozir = Z("2026-10-16T12:00:00Z");
  const kunlar = ["2026-10-14", "2026-10-15"];
  const sessiyalar = [s(1, kunlar[0], 1), s(2, kunlar[0], 2), s(3, kunlar[1], 1)];
  const ustunlar = kunUstunlari(kunlar, sessiyalar, hozir);
  const natijalar = [
    n(1, "Z", "elak", 1),
    n(2, "Z", "elak", 2),
    n(1, "X", "elak", 2),
    n(2, "X", "elak", 1),
    n(1, "Y", "elak", 3),
    n(2, "Y", "elak", 3),
    n(3, "Y", "elak", 1),
  ];
  const seriyalar = oylikBump(ustunlar, sessiyalar, natijalar, 2);
  const nuqta = (sym: string) => seriyalar.find((x) => x.symbol === sym)!.nuqtalar;
  // 1-kun: Z va X ikkalasi 2 marta Top-2 da, o'rtacha 1.5 — symbol: X oldin.
  assert.deepEqual(nuqta("X"), [{ tur: "orin", orin: 1 }, { tur: "chiqdi" }]);
  assert.deepEqual(nuqta("Z"), [{ tur: "orin", orin: 2 }, { tur: "chiqdi" }]);
  assert.deepEqual(nuqta("Y"), [
    { tur: "tashqarida", orin: 3 },
    { tur: "orin", orin: 1 },
  ]);
});

// --------------------------------------------------------------------------- //
//  Sessiya jadvali
// --------------------------------------------------------------------------- //

test("jadval: foiz oldingi MAVJUD sessiyadan, kunlar narx orqali bog'lanadi", () => {
  const hozir = new Date(tasdiqVaqti(KUN, 4).getTime() + 30 * 60_000);
  const ustunlar = sessiyaUstunlari([KUN], [s(11, KUN, 1), s(12, KUN, 2), s(14, KUN, 4)], hozir);
  const OLDINGI = 6; // kechagi 6-sessiya (01:45)
  const natijalar = [
    n(OLDINGI, "AAA", "elak", 2, 100),
    n(OLDINGI, "BBB", "elak", 15, 10), // Top-10 da emas, lekin O'RIN bor
    n(OLDINGI, "CCC", "elak", 1, 50),
    n(11, "AAA", "elak", 1, 110),
    n(11, "BBB", "elak", 3, 12),
    n(11, "CCC", "chiqdi", null, 45),
    n(11, "DDD", "elak", 5, 20),
    n(11, "EEE", "namuna", null, 4),
    n(12, "AAA", "elak", 4, 99, "tasdiqlangan"),
    n(12, "DDD", "elak", 12, 30),
    n(12, "EEE", "elak", 2, 5),
    n(14, "AAA", "elak", 1, 108.9),
  ];
  const jadval = sessiyaJadvali(ustunlar, natijalar, OLDINGI, 10);
  assert.deepEqual(
    jadval.map((q) => q.symbol),
    // Oxirgi ustundagi o'rin: AAA #1; qolganlari — oynadagi eng yaxshi o'rin.
    ["AAA", "EEE", "BBB", "DDD", "CCC"],
  );
  const katak = (sym: string) => jadval.find((q) => q.symbol === sym)!.kataklar;
  const yaxlit = (x: number | null) => (x === null ? null : Math.round(x * 100) / 100);

  const aaa = katak("AAA");
  assert.equal(aaa[0].tur, "orin");
  // Kunning 1-sessiyasi — kechagi oxirgisidan: 110 / 100.
  assert.equal(yaxlit((aaa[0] as { foiz: number }).foiz), 10);
  assert.deepEqual({ ...aaa[1], foiz: yaxlit((aaa[1] as { foiz: number }).foiz) }, {
    tur: "orin",
    orin: 4,
    foiz: -10,
    tasdiqlangan: true,
  });
  assert.deepEqual(aaa[2], { tur: "otkazildi" });
  // O'tkazib yuborilgan ustundan keyin — oldingi MAVJUD (12) dan: 108.9 / 99.
  assert.equal(yaxlit((aaa[3] as { foiz: number }).foiz), 10);

  // O'rin Top-N dan tashqarida bo'lsa ham foiz hisoblanadi.
  assert.equal(yaxlit((katak("BBB")[0] as { foiz: number }).foiz), 20);
  assert.deepEqual(katak("BBB")[1], { tur: "yoq" });
  // chiqdi — narxi yozilgan, foizi bor.
  assert.equal(katak("CCC")[0].tur, "chiqdi");
  assert.equal(yaxlit((katak("CCC")[0] as { foiz: number }).foiz), -10);
  // Oldingi sessiyada ro'yxatda yo'q — foiz yo'q.
  assert.deepEqual(katak("DDD")[0], { tur: "orin", orin: 5, foiz: null, tasdiqlangan: false });
  assert.equal(yaxlit((katak("DDD")[1] as { foiz: number }).foiz), 50);
  // Oldingi sessiyada faqat namuna (o'rinsiz) — foiz HISOBLANMAYDI.
  assert.deepEqual(katak("EEE")[1], { tur: "orin", orin: 2, foiz: null, tasdiqlangan: false });
});

test("jadval: oldingi sessiya bo'lmasa birinchi ustunda foiz yo'q", () => {
  const hozir = new Date(tasdiqVaqti(KUN, 1).getTime() + 30 * 60_000);
  const ustunlar = sessiyaUstunlari([KUN], [s(11, KUN, 1)], hozir);
  const jadval = sessiyaJadvali(ustunlar, [n(11, "AAA", "elak", 1, 10)], null, 10);
  assert.deepEqual(jadval[0].kataklar, [{ tur: "orin", orin: 1, foiz: null, tasdiqlangan: false }]);
});

// --------------------------------------------------------------------------- //
//  Calibration
// --------------------------------------------------------------------------- //

const tek = (kod: Tekshiruv["kod"], holat: Tekshiruv["holat"]): Tekshiruv => ({
  kod,
  guruh: kod === "hajm" || kod === "narx" || kod === "btc" ? "harakat" : "yoqilgi",
  holat,
  qiymat: null,
  chegara: null,
  manba: "",
  qoshimcha: {},
});
const kq = (
  turi: string,
  nomzod: boolean,
  tasdiqSoni: number,
  hajm: Tekshiruv["holat"],
  kel24Max: number | null,
  kel7Max: number | null = null,
  kel24Min: number | null = null,
): KalibrQator => ({
  turi,
  nomzod,
  tasdiqSoni,
  tekshiruvlar: [tek("hajm", hajm)],
  kel24Max,
  kel24Min,
  kel7Max,
  kel7Min: null,
});

test("calibration: guruhlar, tekshiruvlar va tasdiq soni bo'yicha ulush", () => {
  const h = kalibrovka(
    [
      kq("elak", true, 4, "ha", 25, 60, -5),
      kq("elak", true, 4, "ha", 10, null, -15),
      kq("elak", true, 5, "yoq", 30, 40),
      kq("elak", false, 1, "yoq", 5),
      kq("elak", false, 2, "yoq", 21),
      kq("namuna", false, 0, "malumot_yoq", 50, 80),
      kq("chiqdi", false, 0, "ha", 99, 99), // faqat narx — hisobga kirmaydi
      kq("elak", true, 4, "ha", null, null), // hali baholanmagan
    ],
    { portlash24: 20, portlash7: 50 },
  );
  assert.equal(h.jami24, 6);
  assert.equal(h.jami7, 3);
  assert.deepEqual(h.guruhlar.nomzod.kun24, { n: 3, portlash: 2, ulush: (2 / 3) * 100 });
  assert.deepEqual(h.guruhlar.nomzod.kun7, { n: 2, portlash: 1, ulush: 50 });
  assert.deepEqual(h.guruhlar.nomzod_emas.kun24, { n: 2, portlash: 1, ulush: 50 });
  assert.deepEqual(h.guruhlar.namuna.kun24, { n: 1, portlash: 1, ulush: 100 });
  assert.equal(h.guruhlar.nomzod.ortachaMin24, -10);
  assert.equal(h.guruhlar.nomzod.ortachaMax24, (25 + 10 + 30) / 3);
  assert.ok(h.guruhlar.nomzod.kam, "n < 30 — ogohlantirish");

  assert.deepEqual(h.tekshiruvlar.hajm.ha.kun24, { n: 2, portlash: 1, ulush: 50 });
  assert.deepEqual(h.tekshiruvlar.hajm.yoq.kun24, { n: 3, portlash: 2, ulush: (2 / 3) * 100 });
  assert.equal(h.tekshiruvlar.hajm.malumotYoq, 1);
  // Qatorda umuman yo'q tekshiruv — "ma'lumot yo'q".
  assert.equal(h.tekshiruvlar.oi.malumotYoq, 6);

  assert.equal(h.tasdiqSoni.length, 8);
  assert.deepEqual(h.tasdiqSoni[4].kun24, { n: 2, portlash: 1, ulush: 50 });
  assert.deepEqual(h.tasdiqSoni[7].kun24, { n: 0, portlash: 0, ulush: null });
});

test("calibration: 30 va undan ko'p yozuvda ogohlantirish yo'q", () => {
  const qatorlar = Array.from({ length: 30 }, (_, i) => kq("namuna", false, 0, "yoq", i));
  assert.equal(kalibrovka(qatorlar, { portlash24: 20, portlash7: 50 }).guruhlar.namuna.kam, false);
});

// --------------------------------------------------------------------------- //
//  Sozlamalar va yashirish
// --------------------------------------------------------------------------- //

test("sozlama: oraliq, butun son, noma'lum kalit", () => {
  assert.deepEqual(sozlamaTekshir("hajm_x", 5), { ok: true, kalit: "hajm_x", qiymat: 5 });
  assert.equal(sozlamaTekshir("hajm_x", 1).ok, true); // chegara kiradi
  assert.equal(sozlamaTekshir("hajm_x", 100).ok, true);
  assert.deepEqual(sozlamaTekshir("hajm_x", 0.5), { ok: false, xato: "oraliq" });
  assert.deepEqual(sozlamaTekshir("top_n", 10.5), { ok: false, xato: "butun" });
  assert.deepEqual(sozlamaTekshir("top_n", 2), { ok: false, xato: "oraliq" });
  assert.deepEqual(sozlamaTekshir("funding_8s_pct", 0.0005), { ok: false, xato: "oraliq" });
  assert.equal(sozlamaTekshir("funding_8s_pct", 0.001).ok, true);
  assert.deepEqual(sozlamaTekshir("yoq_kalit", 1), { ok: false, xato: "kalit" });
  assert.deepEqual(sozlamaTekshir("__proto__", 1), { ok: false, xato: "kalit" });
  assert.deepEqual(sozlamaTekshir("hajm_x", Number.NaN), { ok: false, xato: "son" });
  assert.deepEqual(sozlamaTekshir("hajm_x", Infinity), { ok: false, xato: "son" });
  assert.equal(sonniOqi("10 000 000"), 10_000_000);
  assert.equal(sonniOqi("0,1"), 0.1);
  assert.ok(Number.isNaN(sonniOqi("")));
  assert.ok(Number.isNaN(sonniOqi("abc")));
});

test("standart qiymatlar o'z oralig'ida va butun kalitlar butun", () => {
  assert.equal(SOZLAMA_KALITLARI.length, 18);
  for (const k of SOZLAMA_KALITLARI) {
    assert.ok(sozlamaTekshir(k, SOZLAMA_STANDART[k]).ok, `${k} standarti oraliqdan tashqarida`);
  }
  for (const k of BUTUN_KALITLAR) assert.ok(Number.isInteger(SOZLAMA_STANDART[k]));
});

test("SOZLAMA_ORALIQLARI hujjatdagi (15-bo'lim) jadval bilan bir xil", () => {
  const hujjat = readFileSync(path.resolve(process.cwd(), "..", "docs", "MODUL_4_0_0.md"), "utf8");
  const son = (x: string) => Number(x.replace(/\s/g, "").replace("10¹¹", "1e11"));
  const korilgan = new Set<string>();
  for (const m of hujjat.matchAll(/^\| ([a-z_0-9]+) \| ([\d .]+) \| ([\d.¹ ]+?) \.\. ([\d.¹ ]+?) \|$/gm)) {
    const kalit = m[1] as keyof typeof SOZLAMA_ORALIQLARI;
    korilgan.add(kalit);
    assert.ok(kalit in SOZLAMA_ORALIQLARI, `hujjatdagi ${kalit} saytda yo'q`);
    assert.deepEqual([...SOZLAMA_ORALIQLARI[kalit]], [son(m[3]), son(m[4])], kalit);
    assert.equal(SOZLAMA_STANDART[kalit], son(m[2]), `${kalit} standarti`);
  }
  assert.equal(korilgan.size, 18, "hujjat jadvali o'qilmadi");
});

test("SOZLAMA_ORALIQLARI bloki Python o'qiy oladigan shaklda", () => {
  // Python testi blokni regex bilan o'qiydi: bir qatorda bitta kalit.
  const matn = readFileSync(path.join(process.cwd(), "src", "lib", "radar.ts"), "utf8");
  const blok = matn.match(
    /export const SOZLAMA_ORALIQLARI: Record<SozlamaKalit, readonly \[number, number\]> = \{\n([\s\S]*?)\n\};/,
  );
  assert.ok(blok, "blok topilmadi");
  const qatorlar = blok[1].split("\n");
  assert.equal(qatorlar.length, 18);
  for (const q of qatorlar) assert.match(q, /^ {2}[a-z_0-9]+: \[[\d.e]+, [\d.e]+\],$/);
  assert.match(
    matn,
    /export const BUTUN_KALITLAR: readonly SozlamaKalit\[\] = \["yangi_listing_kun", "unlock_kun", "nomzod_min", "top_n", "namuna_soni"\];/,
  );
});

test("sozlama_json buzuq bo'lsa ham yiqilmaydi", () => {
  assert.deepEqual(sozlamaJsonOqi("{buzuq"), {});
  assert.deepEqual(sozlamaJsonOqi('{"top_n": 12, "yoq": 1, "hajm_x": "5"}'), { top_n: 12 });
  assert.deepEqual(sozlamaJsonOqi("[1,2]"), {});
});

test("symbol Binance ko'rinishiga keltiriladi", () => {
  assert.equal(symbolNormalla("lsk"), "LSKUSDT");
  assert.equal(symbolNormalla("LSKUSDT"), "LSKUSDT");
  assert.equal(symbolNormalla(" lsk/usdt "), "LSKUSDT");
  assert.equal(symbolNormalla("1000pepe"), "1000PEPEUSDT");
  assert.equal(symbolNormalla(""), null);
  assert.equal(symbolNormalla(null), null);
  assert.equal(symbolNormalla("a"), null);
  assert.equal(symbolNormalla("usdt"), null);
  assert.equal(symbolNormalla("LSK;DROP"), null);
  assert.equal(symbolNormalla("X".repeat(31)), null);
});

test("yashirish muddati", () => {
  const hozir = Z("2026-10-14T12:00:00Z");
  assert.equal(yashirishGacha("doimiy", hozir), null);
  assert.equal(iso(yashirishGacha("7", hozir) as Date), "2026-10-21T12:00:00Z");
  assert.equal(yashirishGacha("365", hozir), undefined);
  assert.equal(yashirishGacha(null, hozir), undefined);
});

// --------------------------------------------------------------------------- //
//  JSON va kartochka matni
// --------------------------------------------------------------------------- //

test("tekshiruvlar_json — buzuq JSON va buzuq element sahifani yiqitmaydi", () => {
  assert.deepEqual(tekshiruvlarniOqi("{buzuq"), []);
  assert.deepEqual(tekshiruvlarniOqi(null), []);
  assert.deepEqual(tekshiruvlarniOqi('{"kod": "hajm"}'), []);
  const r = tekshiruvlarniOqi(
    JSON.stringify([
      { kod: "taminot", guruh: "yoqilgi", holat: "yoq", qiymat: 70.6, chegara: 60, manba: "x" },
      null,
      "matn",
      { kod: "nomalum", holat: "ha" },
      { kod: "hajm", holat: "ajabtovur", qiymat: "8.2", qoshimcha: [1] },
      { kod: "hajm", holat: "ha" }, // takror — tashlanadi
    ]),
  );
  assert.deepEqual(
    r.map((t) => [t.kod, t.guruh, t.holat, t.qiymat]),
    [
      ["hajm", "harakat", "malumot_yoq", 8.2], // noma'lum holat — "ma'lumot yo'q", ✅ EMAS
      ["taminot", "yoqilgi", "yoq", 70.6],
    ],
  );
  assert.deepEqual(r[0].qoshimcha, {});
});

test("manbalar: 451 — mintaqa cheklangan", () => {
  const m = manbalarniOqi('{"ticker": {"holat": "xato", "kod": 451, "izoh": "restricted"}, "coingecko": {"holat": "ok", "kod": 200}}');
  assert.equal(m.length, 2);
  assert.ok(mintaqaCheklanganmi(m));
  assert.ok(!mintaqaCheklanganmi(manbalarniOqi('{"ticker": {"holat": "xato", "kod": 500}}')));
  assert.deepEqual(manbalarniOqi("buzuq"), []);
});

const T = (kod: Tekshiruv["kod"], qiymat: number | null, chegara: number | null, qoshimcha = {}): Tekshiruv => ({
  ...tek(kod, "ha"),
  qiymat,
  chegara,
  qoshimcha,
});

test("tekshiruv izohi — hujjatdagi kartochka namunasi", () => {
  assert.deepEqual(tekshiruvSababi(T("hajm", 8.2, 5)), {
    kalit: "hajm",
    qiymatlar: { x: "8.2", c: "5", k: "" },
  });
  assert.equal(tekshiruvSababi(T("hajm", null, 5)).kalit, "hajm_yoq");
  assert.deepEqual(tekshiruvSababi(T("narx", 287, 20)).qiymatlar, { x: "+287%", c: "20" });
  assert.deepEqual(tekshiruvSababi(T("funding", -0.34, 0.1, { oraliq_soat: 4 })), {
    kalit: "funding_oraliq",
    qiymatlar: { x: "−0.34%", o: "4", c: "0.1" },
  });
  assert.equal(tekshiruvSababi(T("funding", 0.12, 0.1, { oraliq_soat: 8 })).kalit, "funding");
  assert.deepEqual(tekshiruvSababi(T("oi", 41, 30, { soat: 8 })).qiymatlar, { s: "8", x: "+41%", c: "30" });
  assert.deepEqual(tekshiruvSababi(T("long_short", 1.8, 2.5)), {
    kalit: "long_short_long",
    qiymatlar: { r: "1.8", c: "2.5" },
  });
  assert.deepEqual(tekshiruvSababi(T("long_short", 0.25, 2.5)).qiymatlar, { r: "4.0", c: "2.5" });
  assert.deepEqual(tekshiruvSababi(T("btc", 287.7, 15)).qiymatlar, { x: "+287.7", c: "15" });
  assert.deepEqual(tekshiruvSababi(T("btc", -20, 15)).qiymatlar, { x: "−20.0", c: "15" });
  assert.deepEqual(
    tekshiruvSababi(T("taminot", 70.6, 60, { aylanma_pct: 70.6, unlock_kun: 7, unlock_pct: 0 })),
    { kalit: "taminot_unlock_yoq", qiymatlar: { a: "70.6", k: "7" } },
  );
  assert.equal(
    tekshiruvSababi(T("taminot", 70.6, 60, { aylanma_pct: 70.6, unlock_kun: 7, unlock_pct: 6.5 })).kalit,
    "taminot_unlock",
  );
  assert.equal(tekshiruvSababi(T("taminot", null, 60)).kalit, "taminot_yoq");
});

test("joriy bo'limlar: tasdiqlangan, nomzod, o'tkinchi, boshqalar", () => {
  const nat = (symbol: string, holat: Natija["holat"], nomzod: boolean, orin: number | null, turi = "elak"): Natija => ({
    sessiyaId: 1,
    symbol,
    belgi: symbol,
    turi,
    narx: 1,
    hajm24s: null,
    hajmNisbati: null,
    ozgarish24s: null,
    marketCap: null,
    tekshiruvlar: [],
    tasdiqSoni: 0,
    harakatSoni: 0,
    yoqilgiSoni: 0,
    malumotYoqSoni: 0,
    nomzod,
    holat,
    orin,
    ketmaKet: 1,
    yashirin: orin === null,
    yangiListing: false,
    halol: "baholanmagan",
  });
  const b = joriyBolimlar([
    nat("D", "oddiy", false, 4),
    nat("A", "tasdiqlangan", true, 1),
    nat("B", "nomzod", true, 3),
    nat("C", "vaqtinchalik", false, 2),
    nat("H", "nomzod", true, null),
    nat("N", "oddiy", false, null, "namuna"),
    nat("X", "oddiy", false, null, "chiqdi"),
  ]);
  assert.deepEqual(b.tasdiqlangan.map((x) => x.symbol), ["A"]);
  assert.deepEqual(b.nomzodlar.map((x) => x.symbol), ["B", "H"]); // yashirilgan — oxirida
  assert.deepEqual(b.otkinchi.map((x) => x.symbol), ["C"]);
  assert.deepEqual(b.boshqalar.map((x) => x.symbol), ["D"]);
});

// --------------------------------------------------------------------------- //
//  QAT'IY CHEGARALAR — manba matnini tekshirish
// --------------------------------------------------------------------------- //

const SRC = path.join(process.cwd(), "src");

function fayllar(jild: string): string[] {
  const natija: string[] = [];
  for (const nom of readdirSync(jild)) {
    const toliq = path.join(jild, nom);
    if (statSync(toliq).isDirectory()) natija.push(...fayllar(toliq));
    else if (/\.tsx?$/.test(nom)) natija.push(toliq);
  }
  return natija;
}

/** Signal so'zlari: kirish/stop/nishon narxi, "kirish narxi". */
const SIGNAL_SOZLARI = /\bentry\b|\bstop\b|\btp\d?\b|take[\s-]?profit|kirish narxi|цена входа|стоп-лосс|тейк-профит/i;

test("Modul 4.0.0 sahifasi, komponentlari va matnlarida signal so'zlari yo'q", () => {
  const manbalar = [
    ...fayllar(path.join(SRC, "app", "(ichki)", "modul-4")),
    ...fayllar(path.join(SRC, "components", "radar")),
    path.join(SRC, "lib", "radar.ts"),
    path.join(SRC, "lib", "radar-baza.ts"),
  ];
  assert.ok(manbalar.length >= 8, "fayllar topilmadi");
  const buzuq: string[] = [];
  for (const fayl of manbalar) {
    readFileSync(fayl, "utf8")
      .split("\n")
      .forEach((q, i) => {
        // Izohlarda chegarani TUSHUNTIRISH uchun so'z tilga olinadi.
        const toza = q.trim();
        if (toza.startsWith("*") || toza.startsWith("//") || toza.startsWith("/*")) return;
        if (SIGNAL_SOZLARI.test(q)) buzuq.push(`${path.relative(SRC, fayl)}:${i + 1}: ${toza}`);
      });
  }
  for (const til of ["uz", "ru"]) {
    const lugat = JSON.parse(readFileSync(path.join(SRC, "lib", "i18n", `${til}.json`), "utf8"));
    const radar = JSON.stringify(lugat.radar);
    assert.ok(radar && radar.length > 1000, `${til}: radar bo'limi yo'q`);
    if (SIGNAL_SOZLARI.test(radar)) buzuq.push(`${til}.json radar: ${radar.match(SIGNAL_SOZLARI)?.[0]}`);
  }
  assert.deepEqual(buzuq, []);
});

test("radar i18n bo'limi ikki tilda bir xil kalitlarga ega", () => {
  const kalitlar = (o: Record<string, unknown>, p = ""): string[] =>
    Object.entries(o).flatMap(([k, v]) =>
      v && typeof v === "object" ? kalitlar(v as Record<string, unknown>, `${p}${k}.`) : [`${p}${k}`],
    );
  const oqi = (til: string) =>
    JSON.parse(readFileSync(path.join(SRC, "lib", "i18n", `${til}.json`), "utf8")).radar;
  assert.deepEqual(kalitlar(oqi("ru")).sort(), kalitlar(oqi("uz")).sort());
  // Kod dinamik ishlatadigan kalitlar ham bor bo'lsin.
  const uz = oqi("uz");
  for (const k of SOZLAMA_KALITLARI) assert.ok(uz.kalit[k], `radar.kalit.${k}`);
  for (const k of ["hajm", "narx", "funding", "oi", "long_short", "btc", "taminot"]) {
    assert.ok(uz.tek[k], `radar.tek.${k}`);
  }
  for (const h of ["halol", "harom", "shubhali", "baholanmagan"]) assert.ok(uz.halol[h]);
  for (const kalit of [
    "hajm",
    "hajm_kunlar",
    "hajm_yoq",
    "narx",
    "narx_yoq",
    "funding",
    "funding_oraliq",
    "funding_yoq",
    "oi",
    "oi_yoq",
    "oi_qisqa",
    "long_short_long",
    "long_short_short",
    "long_short_yoq",
    "btc",
    "btc_yoq",
    "taminot",
    "taminot_unlock_yoq",
    "taminot_unlock",
    "taminot_faqat_unlock",
    "taminot_yoq",
  ]) {
    assert.ok(uz.sabab[kalit], `radar.sabab.${kalit}`);
  }
});

test("OI oynasi to'lmagan coin 'tarix yo'q' emas, qisqa tarix deb yoziladi", () => {
  const asos = {
    kod: "oi",
    guruh: "yoqilgi",
    holat: "malumot_yoq",
    qiymat: null,
    chegara: 30,
    manba: "binance_oi",
  } as const;
  assert.equal(tekshiruvSababi({ ...asos, qoshimcha: { soat: 2 } }).kalit, "oi_qisqa");
  assert.equal(tekshiruvSababi({ ...asos, qoshimcha: { soat: 0 } }).kalit, "oi_yoq");
  assert.equal(tekshiruvSababi({ ...asos, qoshimcha: {} }).kalit, "oi_yoq");
});

test("har server amali adminlikni QAYTA tekshiradi", () => {
  const matn = readFileSync(path.join(SRC, "app", "(ichki)", "modul-4", "amallar.ts"), "utf8");
  assert.match(matn, /^"use server";/);
  const amallar = [...matn.matchAll(/export async function (\w+)\([^)]*\)[^{]*\{([\s\S]*?)\n\}/g)];
  assert.deepEqual(
    amallar.map((m) => m[1]).sort(),
    ["coinOch", "coinYashir", "radarniSora", "sozlamaSaqla", "sozlamaTikla"],
  );
  for (const [, nom, tana] of amallar) {
    const kirimJoyi = tana.indexOf("await kirim()");
    const tekshiruv = tana.indexOf("if (!admin) return;");
    assert.ok(kirimJoyi >= 0, `${nom}: kirim() chaqirilmagan`);
    assert.ok(tekshiruv > kirimJoyi, `${nom}: admin tekshirilmagan`);
    // Bazaga yozish adminlik tekshiruvidan KEYIN.
    const yozish = tana.search(/radarSora\(|sozlamaYoz\(|sozlamaOchir\(|yashirinQosh\(|yashirinOchir\(/);
    assert.ok(yozish > tekshiruv, `${nom}: yozish tekshiruvdan oldin`);
  }
  // Fayldagi boshqa eksport yo'q (yashirin amal qolib ketmasin).
  assert.equal([...matn.matchAll(/^export /gm)].length, amallar.length);
});

test("sahifa admin bo'lmaganga hech narsa so'ramaydi", () => {
  const matn = readFileSync(path.join(SRC, "app", "(ichki)", "modul-4", "page.tsx"), "utf8");
  const tekshiruv = matn.indexOf("if (!admin)");
  assert.ok(tekshiruv > 0);
  assert.ok(matn.includes('t("admin.faqat_admin")'));
  for (const chaqiriq of ["radarTayyorligi(", "radarHolati(", "oxirgiSessiya(", "searchParams;"]) {
    assert.ok(matn.indexOf(chaqiriq) > tekshiruv, `${chaqiriq} admin tekshiruvidan oldin`);
  }
  assert.match(matn, /export const dynamic = "force-dynamic";/);
});

test("radar.ts sof: node moduli, baza va config import qilinmaydi", () => {
  const matn = readFileSync(path.join(SRC, "lib", "radar.ts"), "utf8");
  const importlar = [...matn.matchAll(/^import[\s\S]*?from\s+"([^"]+)"/gm)].map((m) => m[1]);
  const yomon = importlar.filter((m) => /^node:|db(\.ts)?$|config(\.ts)?$|radar-baza|session|queries/.test(m));
  assert.deepEqual(yomon, []);
  assert.ok(!/require\(|process\.|readFileSync/.test(matn));
});

test("radar-baza.ts faqat ruxsat etilgan uchta jadvalga yozadi", () => {
  const matn = readFileSync(path.join(SRC, "lib", "radar-baza.ts"), "utf8");
  const jadvallar = new Set<string>();
  for (const m of matn.matchAll(/\b(?:insert\s+into|delete\s+from)\s+(\w+)|\bupdate\s+(\w+)\s+set\b/gi)) {
    jadvallar.add((m[1] ?? m[2]).toLowerCase());
  }
  assert.deepEqual([...jadvallar].sort(), ["radar_holati", "radar_sozlamalar", "radar_yashirin"]);
  // Foydalanuvchi qiymati SQL ga yopishtirilmaydi: shablon ichida faqat
  // ustunlar ro'yxati, tartib va joy belgilari bor.
  const ichki = [...matn.matchAll(/\$\{(\w+)\}/g)].map((m) => m[1]);
  assert.deepEqual([...new Set(ichki)].sort(), ["SESSIYA_USTUNLARI", "joylar", "tartib"]);
});
