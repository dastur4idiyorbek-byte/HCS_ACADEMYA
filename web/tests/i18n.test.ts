import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import { kalkulyatorMatnlari, kartochkaMatnlari, tarjima } from "../src/lib/i18n/index.ts";

/** Bu test 2-naqshga qarshi: "e'lon qilingan, lekin ulanmagan".
 *
 * `tarjima()` kalit topilmasa XATO BERMAYDI — kalitning O'ZINI
 * qaytaradi. Bu ataylab shunday (bitta yetishmagan matn sahifani
 * yiqitmasligi kerak), lekin narxi bor: kalitni noto'g'ri bo'limga
 * yozib qo'ysak, ekranda `portfel.balans_kerak` degan xom matn chiqadi
 * va buni faqat tasodifan ko'rib qolamiz.
 *
 * Aynan shu IKKI MARTA sodir bo'ldi:
 *   - `admin.izoh` mavjud tarjimani bosib ketgan edi;
 *   - `balans_kerak` `signal` bo'limiga tushib qolgan, sahifa esa
 *     `portfel.balans_kerak` deb o'qirdi.
 *
 * Endi kodda ishlatilgan HAR BIR kalit tekshiriladi.
 */

const ILDIZ = path.resolve(process.cwd(), "src");

function fayllar(jild: string): string[] {
  const natija: string[] = [];
  for (const nom of readdirSync(jild)) {
    const toliq = path.join(jild, nom);
    if (statSync(toliq).isDirectory()) natija.push(...fayllar(toliq));
    else if (/\.tsx?$/.test(nom)) natija.push(toliq);
  }
  return natija;
}

/** `t("bolim.kalit")` — faqat QATTIQ yozilgan kalitlar.
 *  O'zgaruvchi orqali berilganlarini statik topib bo'lmaydi. */
const NAQSH = /\bt\(\s*"([a-z0-9_]+\.[a-z0-9_]+)"\s*\)/gi;

test("kodda ishlatilgan har bir tarjima kaliti mavjud", () => {
  const yetishmayotgan: string[] = [];
  const kalitlar = new Set<string>();

  for (const fayl of fayllar(ILDIZ)) {
    const matn = readFileSync(fayl, "utf8");
    for (const moslik of matn.matchAll(NAQSH)) {
      const kalit = moslik[1];
      kalitlar.add(kalit);
      // Kalit topilmasa `tarjima()` kalitning o'zini qaytaradi.
      if (tarjima("uz", kalit) === kalit) {
        yetishmayotgan.push(`${path.relative(ILDIZ, fayl)}: ${kalit}`);
      }
    }
  }

  assert.ok(kalitlar.size > 50, `juda kam kalit topildi (${kalitlar.size}) — naqsh buzilganmi?`);
  assert.deepEqual(yetishmayotgan, [], "bu kalitlar lug'atda yo'q");
});

test("ruscha tarjimada ham shu kalitlar bor", () => {
  const yetishmayotgan: string[] = [];
  for (const fayl of fayllar(ILDIZ)) {
    for (const moslik of readFileSync(fayl, "utf8").matchAll(NAQSH)) {
      const kalit = moslik[1];
      // `tarjima("ru", ...)` topolmasa uzbekchaga tushadi — shuning
      // uchun lug'atning O'ZIDAN qaraymiz.
      if (!ruDaBormi(kalit)) yetishmayotgan.push(kalit);
    }
  }
  assert.deepEqual([...new Set(yetishmayotgan)], [], "ruscha tarjimasi yo'q kalitlar");
});

function ruDaBormi(kalit: string): boolean {
  const ru = JSON.parse(
    readFileSync(path.join(ILDIZ, "lib", "i18n", "ru.json"), "utf8"),
  ) as Record<string, unknown>;
  let joriy: unknown = ru;
  for (const qism of kalit.split(".")) {
    if (typeof joriy !== "object" || joriy === null) return false;
    joriy = (joriy as Record<string, unknown>)[qism];
  }
  return typeof joriy === "string";
}

test("kalkulyator matnlari kartochka matnlarini BOSIB KETMAYDI", () => {
  // Bir vaqtlar `kalkulyatorMatnlari` ichida `kirish: t("signal.kalk_kirish")`
  // turardi va u `kartochkaMatnlari` dagi `kirish: t("signal.kart_kirish")`
  // ni bosib ketardi. Natijada BITTA signal ikki xil ko'rinardi:
  // ro'yxatda "Kirish narxi", o'z sahifasida "Kirish". Kartochka esa
  // botdagi shablonning aynan nusxasi bo'lishi shart.
  const t = (kalit: string) => kalit;
  const kartochka = kartochkaMatnlari(t);
  const kalkulyator = kalkulyatorMatnlari(t) as Record<string, string>;

  for (const [nom, qiymat] of Object.entries(kartochka)) {
    assert.equal(
      kalkulyator[nom],
      qiymat,
      `"${nom}" kalkulyator ro'yxatida boshqa matnga almashib qolgan`,
    );
  }
});

test("salomatlik omillari 0..1 shkalasida saqlanadi va foizga aylantiriladi", () => {
  // SHKALA MOS KELMASLIGI (1-naqsh) — bu loyihada takrorlangan xato turi.
  //
  // Bot `HealthFactor.score` ni o'zgartirmasdan yozadi (0..1). Sahifa
  // esa uni to'g'ridan-to'g'ri foiz deb chizardi: haqiqiy ma'lumotda
  // har bir omil "0" yoki "1" ko'rinardi. Demo ma'lumot 0-100 shkalada
  // yozilgani uchun xato bir necha oy sezilmadi.
  //
  // Shuning uchun ikkalasi ham shu yerda qulflanadi.
  const sahifa = readFileSync(
    path.join(ILDIZ, "app", "(ichki)", "salomatlik", "page.tsx"),
    "utf8",
  );
  assert.match(sahifa, /function omilFoizi/, "foizga aylantirish funksiyasi yo'q");
  assert.match(sahifa, /\* 100/, "0..1 dan foizga o'tkazish yo'qolgan");

  const demo = readFileSync(
    path.join(ILDIZ, "..", "scripts", "demo_malumot.mjs"),
    "utf8",
  );
  const qator = /\.run\(qiymat,[\s\S]*?oldin\(i \* 4\)\)/.exec(demo)?.[0] ?? "";
  const sonlar = [...qator.matchAll(/0\.\d+/g)].map((m) => Number(m[0]));
  assert.ok(sonlar.length >= 5, "demo omil ballari topilmadi");
  assert.ok(
    sonlar.every((x) => x >= 0 && x <= 1),
    `demo ma'lumot 0..1 shkalasida bo'lishi kerak, hozir: ${sonlar.join(", ")}`,
  );
});
