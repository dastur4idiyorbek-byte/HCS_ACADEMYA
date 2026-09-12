import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { MENYU } from "../src/lib/menyu.ts";
import {
  SEGMENT_KALITI,
  SEGMENT_SONI,
  blokRangi,
  yonalishBelgisi,
  zonaJoyi,
  type KuzatuvBlok,
} from "../src/lib/kuzatuv.ts";

const ILDIZ = path.join(import.meta.dirname, "..", "..");

function oqi(nisbiy: string): string {
  return readFileSync(path.join(ILDIZ, nisbiy), "utf8");
}

// --------------------------------------------------------------------------- //
//  CHEGARA — sayt tomonida ham Entry/Stop/TP yo'q
// --------------------------------------------------------------------------- //

const SAYT_FAYLLARI = [
  "web/src/lib/kuzatuv.ts",
  "web/src/components/kuzatuv/Segmentlar.tsx",
  "web/src/components/kuzatuv/CoinQatori.tsx",
  "web/src/app/(ichki)/kuzatuv/page.tsx",
  "web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx",
];

test("kuzatuv sahifalari savdo darajasi hisoblamaydi", () => {
  // `kalkulyator` va `signal.kalk_*` — Entry/Stop/TP bilan ishlaydigan
  // mavjud modullar. Ular kuzatuv paneliga KIRMASLIGI kerak.
  const taqiq = ["kalkulyatorMatnlari", "signalLevels", "darajalarQur", "@/lib/kalkulyator"];
  for (const fayl of SAYT_FAYLLARI) {
    const matn = oqi(fayl);
    for (const nom of taqiq) {
      assert.ok(!matn.includes(nom), `${fayl}: taqiqlangan "${nom}" ishlatilgan`);
    }
  }
});

test("chegara ro'yxati bo'sh emas", () => {
  // Ro'yxat bo'shab qolsa yuqoridagi test YOLG'ON yashil berardi.
  assert.ok(SAYT_FAYLLARI.length >= 5);
  for (const fayl of SAYT_FAYLLARI) {
    assert.ok(oqi(fayl).length > 0, `${fayl} bo'sh`);
  }
});

// --------------------------------------------------------------------------- //
//  Python bilan mos
// --------------------------------------------------------------------------- //

test("segment nomlari Python bilan bir xil", () => {
  const python = oqi("core/analysis/observation_mode.py");
  for (const nom of Object.keys(SEGMENT_KALITI)) {
    assert.ok(
      python.includes(`"${nom}"`),
      `segment "${nom}" Pythonda topilmadi — nomlar ajralib ketgan`,
    );
  }
});

test("segment soni ikki tomonda teng", () => {
  assert.equal(SEGMENT_SONI, Object.keys(SEGMENT_KALITI).length);
});

test("yo'nalish qiymatlari Python bilan bir xil", () => {
  const python = oqi("core/analysis/structure/uptrend_filter.py");
  for (const qiymat of ["uptrend", "yangi_burilish", "downtrend", "aniq_emas"]) {
    assert.ok(python.includes(`"${qiymat}"`), `yo'nalish "${qiymat}" Pythonda yo'q`);
  }
});

test("ro'yxat nomlari Python bilan bir xil", () => {
  const python = oqi("core/watch_panel/repository.py");
  for (const qiymat of ["top", "kuzatuvda", "royxatdan_tashqari"]) {
    assert.ok(python.includes(`"${qiymat}"`), `ro'yxat "${qiymat}" Pythonda yo'q`);
  }
});

// --------------------------------------------------------------------------- //
//  Menyu — faqat admin
// --------------------------------------------------------------------------- //

test("kuzatuv paneli FAQAT adminlarga ko'rinadi", () => {
  const band = MENYU.find((b) => b.kod === "kuzatuv");
  assert.ok(band, "menyuda kuzatuv bandi yo'q");
  assert.equal(band.adminUchun, true);
  assert.equal(band.yol, "/kuzatuv");
});

test("sahifaning O'ZI ham adminlikni tekshiradi", () => {
  // Menyuda yashirish YETARLI EMAS: manzilni bilgan har kim
  // sahifani ochishi mumkin.
  for (const fayl of [
    "web/src/app/(ichki)/kuzatuv/page.tsx",
    "web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx",
  ]) {
    assert.ok(oqi(fayl).includes("if (!admin)"), `${fayl}: adminlik tekshirilmagan`);
  }
});

test("server amali ham adminlikni qayta tekshiradi", () => {
  // Server amali ALOHIDA so'rov bo'lib keladi va layout u uchun
  // yugurmaydi.
  const matn = oqi("web/src/app/(ichki)/kuzatuv/amallar.ts");
  assert.ok(matn.includes("if (!admin) return"));
});

// --------------------------------------------------------------------------- //
//  Zona joyi
// --------------------------------------------------------------------------- //

test("zona joyi: pastki qismda discount", () => {
  assert.equal(zonaJoyi(102, 100, 200), "discount");
});

test("zona joyi: yuqori qismda premium", () => {
  assert.equal(zonaJoyi(190, 100, 200), "premium");
});

test("zona joyi: o'rtada", () => {
  assert.equal(zonaJoyi(150, 100, 200), "ortada");
});

test("zona joyi: ma'lumot yo'q bo'lsa nomalum", () => {
  assert.equal(zonaJoyi(null, 100, 200), "nomalum");
  assert.equal(zonaJoyi(150, null, 200), "nomalum");
  // Teskari oraliq — bo'linish nolga ketmasin
  assert.equal(zonaJoyi(150, 200, 100), "nomalum");
  assert.equal(zonaJoyi(Number.NaN, 100, 200), "nomalum");
});

// --------------------------------------------------------------------------- //
//  Ko'rinish qoidalari
// --------------------------------------------------------------------------- //

test("yo'nalish ikonkasi har qiymat uchun bor", () => {
  const nomlar = new Set(
    (["uptrend", "yangi_burilish", "downtrend", "aniq_emas"] as const).map(
      yonalishBelgisi,
    ),
  );
  assert.equal(nomlar.size, 4, "ikki yo'nalish bir xil ikonka olgan");
});

test("o'lchanmagan blok 'yo'q' EMAS — uchinchi rang", () => {
  const asos = { nom: "Fundamental", kuch: 0, maxraj: 0, tosiq: null, tekshiruvlar: [] };
  const olchanmadi: KuzatuvBlok = { ...asos, otdi: true, olchanmadi: true };
  const otmadi: KuzatuvBlok = { ...asos, maxraj: 4, otdi: false, olchanmadi: false };
  const otdi: KuzatuvBlok = { ...asos, maxraj: 4, kuch: 2, otdi: true, olchanmadi: false };

  assert.equal(blokRangi(olchanmadi), "sokin");
  assert.equal(blokRangi(otmadi), "past");
  assert.equal(blokRangi(otdi), "yaxshi");
});

// --------------------------------------------------------------------------- //
//  Tarjima
// --------------------------------------------------------------------------- //

test("uz va ru da bir xil kuzatuv kalitlari bor", () => {
  const uz = JSON.parse(oqi("web/src/lib/i18n/uz.json")) as Record<string, unknown>;
  const ru = JSON.parse(oqi("web/src/lib/i18n/ru.json")) as Record<string, unknown>;

  const kalitlar = (obj: unknown, oldin = ""): string[] => {
    if (typeof obj !== "object" || obj === null) return [oldin];
    return Object.entries(obj).flatMap(([k, v]) => kalitlar(v, oldin ? `${oldin}.${k}` : k));
  };

  const uzKalit = kalitlar(uz.kuzatuv).sort();
  const ruKalit = kalitlar(ru.kuzatuv).sort();
  assert.ok(uzKalit.length > 20, "kuzatuv tarjimasi juda kam");
  assert.deepEqual(uzKalit, ruKalit, "uz va ru kalitlari mos emas");
});

test("har bir segment kaliti tarjimada bor", () => {
  const uz = JSON.parse(oqi("web/src/lib/i18n/uz.json")) as Record<string, unknown>;
  for (const kalit of Object.values(SEGMENT_KALITI)) {
    const yol = kalit.split(".");
    let joriy: unknown = uz;
    for (const bolak of yol) {
      joriy = (joriy as Record<string, unknown>)?.[bolak];
    }
    assert.equal(typeof joriy, "string", `tarjima yo'q: ${kalit}`);
  }
});
