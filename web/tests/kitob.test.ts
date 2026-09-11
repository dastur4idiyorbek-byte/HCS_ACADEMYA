import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import {
  KITOB_BOLIMLARI,
  KITOB_FAYLI,
  KITOB_TARIFI,
  bolimYonidagi,
} from "../src/lib/kitob.ts";
import { MENYU } from "../src/lib/menyu.ts";

// --------------------------------------------------------------------------- //
//  Kitob himoyasi
// --------------------------------------------------------------------------- //

test("kitob fayli `public/` da TURMAYDI", () => {
  // ENG MUHIM TEKSHIRUV. `public/` ichidagi fayl manzilini bilgan har
  // kimga ochiq bo'ladi — obuna tekshiruvi butunlay chetlab o'tilardi.
  // Video darsliklar ham aynan shu sababdan `api/video` orqali
  // beriladi; kitob undan farq qilmasligi kerak.
  const ochiq = path.resolve(import.meta.dirname, "..", "public", KITOB_FAYLI);
  assert.equal(
    existsSync(ochiq),
    false,
    `Kitob ${ochiq} da turibdi — u hammaga ochiq bo'lib qoladi.`,
  );
  const ochiqJild = path.resolve(import.meta.dirname, "..", "public", "kitob");
  assert.equal(existsSync(ochiqJild), false, "public/kitob/ bo'lmasligi kerak");
});

test("kitob fayli himoyalangan jildda turibdi", () => {
  const yol = path.resolve(import.meta.dirname, "..", "kitob", KITOB_FAYLI);
  assert.ok(existsSync(yol), `Kitob topilmadi: ${yol}`);
});

test("yuklash yo'li obunani tekshiradi", () => {
  // Kodni O'QIB tekshiramiz: HTTP so'rovsiz ham darvoza borligiga
  // ishonch hosil qilish kerak. Kimdir tekshiruvni olib tashlasa,
  // shu test yiqiladi.
  const manba = readFileSync(
    path.resolve(import.meta.dirname, "..", "src", "app", "api", "kitob", "route.ts"),
    "utf8",
  );
  assert.match(manba, /tarifQamraydi\(tarif, KITOB_TARIFI\)/);
  assert.match(manba, /status:\s*403/);
});

test("menyudagi band ham o'sha tarifni talab qiladi", () => {
  // Ikki joyda ikki xil tarif bo'lsa, menyuda ko'rinadigan, lekin
  // ochilmaydigan bo'lim paydo bo'lardi.
  const band = MENYU.find((b) => b.kod === "kitob");
  assert.ok(band, "menyuda kitob bandi yo'q");
  assert.equal(band.talab, KITOB_TARIFI);
});

test("kitob tarkibi barcha bo'limni qamraydi", () => {
  // Olti asosiy bo'lim + kirish va yakuniy bob.
  assert.equal(KITOB_BOLIMLARI.length, 8);
  const boblar = KITOB_BOLIMLARI.map((b) => b.boblar).join(" ");
  for (const bob of ["1–7", "8–10", "11–16", "17–18", "19–20", "21–23", "24"]) {
    assert.ok(boblar.includes(bob), `tarkibda ${bob} yo'q`);
  }
});

test("sayt kalitlari EKSPORT kalitlari bilan bir xil", () => {
  // ENG MUHIM BOG'LANISH. Sayt bo'limni kalit bo'yicha topadi.
  // Ikki joyda ikki xil kalit bo'lsa, mundarijadagi havola
  // "bo'lim topilmadi" sahifasiga olib borardi — va buni faqat
  // bosib ko'rgandagina sezish mumkin.
  const eksport = readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "scripts", "kitob", "eksport.py"),
    "utf8",
  );
  for (const b of KITOB_BOLIMLARI) {
    assert.match(
      eksport,
      new RegExp(`\\("${b.kalit}",`),
      `eksport.py da "${b.kalit}" bo'limi yo'q`,
    );
  }
});

test("mazmun fayli yasalgan va barcha bo'limni o'z ichiga oladi", () => {
  const yol = path.resolve(import.meta.dirname, "..", "kitob", "mazmun.json");
  assert.ok(existsSync(yol), `mazmun.json topilmadi: ${yol}`);
  const d = JSON.parse(readFileSync(yol, "utf8")) as {
    bolimlar: { kalit: string; boblar: unknown[] }[];
  };
  const kalitlar = new Set(d.bolimlar.map((b) => b.kalit));
  for (const b of KITOB_BOLIMLARI) {
    assert.ok(kalitlar.has(b.kalit), `mazmunda "${b.kalit}" yo'q`);
  }
  // 24 bob + kirish = 25.
  const jami = d.bolimlar.reduce((s, b) => s + b.boblar.length, 0);
  assert.equal(jami, 25, "boblar soni kutilganidan farq qiladi");
});

test("bo'limlar zanjiri uzilmagan", () => {
  // Birinchisining oldingisi va oxirgisining keyingisi yo'q;
  // qolganlari bir-biriga ulanadi.
  const birinchi = KITOB_BOLIMLARI[0].kalit;
  const oxirgi = KITOB_BOLIMLARI[KITOB_BOLIMLARI.length - 1].kalit;
  assert.equal(bolimYonidagi(birinchi).oldingi, null);
  assert.equal(bolimYonidagi(oxirgi).keyingi, null);
  for (let i = 0; i < KITOB_BOLIMLARI.length - 1; i++) {
    assert.equal(
      bolimYonidagi(KITOB_BOLIMLARI[i].kalit).keyingi,
      KITOB_BOLIMLARI[i + 1].kalit,
    );
  }
});
