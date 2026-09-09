import assert from "node:assert/strict";
import { test } from "node:test";

import {
  BLOK_NOMLARI,
  blokKorinishi,
  salomatlikIndeksi,
  toliqZanjir,
  xulosaHisobla,
  type Blok,
  type CoinZanjiri,
} from "../src/lib/zanjir.ts";

function blok(
  kuch: number,
  maxraj: number,
  qoshimcha: Partial<Blok> = {},
): Blok {
  return {
    nom: "Struktura",
    kuch,
    maxraj,
    otdi: kuch > 0,
    olchanmadi: maxraj === 0,
    tosiq: "",
    ...qoshimcha,
  };
}

function coin(
  nom: string,
  bloklar: Blok[],
  qoshimcha: Partial<CoinZanjiri> = {},
): CoinZanjiri {
  return {
    symbol: nom,
    bloklar,
    toliq: false,
    uzildiBlokda: null,
    ishonch: 0,
    natija: "zanjir_uzildi",
    izoh: "",
    signalId: null,
    tekshirilgan: new Date("2026-09-04T12:00:00Z"),
    ...qoshimcha,
  };
}

// --------------------------------------------------------------------- //
//  Blokning ko'rinishi
// --------------------------------------------------------------------- //

test("to'liq bog'langan blok YORQIN bo'ladi", () => {
  assert.equal(blokKorinishi(blok(4, 4)), "toliq");
  assert.equal(blokKorinishi(blok(1, 1)), "toliq");
});

test("qisman bog'langan blok ZAIFROQ ko'rinadi", () => {
  assert.equal(blokKorinishi(blok(2, 4)), "qisman");
});

/** 0/4 — zanjir shu yerda uziladi. Qisman bilan bir xil ko'rinsa,
 *  admin "nega signal yo'q" savoliga javob topa olmasdi. */
test("bo'sh blok UZILGAN bo'ladi", () => {
  assert.equal(blokKorinishi(blok(0, 4, { otdi: false })), "uzilgan");
});

test("o'lchanmagan blok zanjirni UZMAYDI", () => {
  assert.equal(blokKorinishi(blok(0, 0, { olchanmadi: true })), "olchanmadi");
});

test("umuman yurmagan blok XIRA bo'ladi", () => {
  assert.equal(blokKorinishi(undefined), "tekshirilmagan");
});

/** Zanjir ekranda HAR DOIM to'rt bo'g'in bo'lishi kerak: Fundamental
 *  da uzilgan coin bitta kvadrat bo'lib qolsa, "qayerda uzildi"
 *  savoliga ko'rinish javob bermasdi. */
test("zanjir har doim TO'RT o'ringa yoyiladi", () => {
  const yoyilgan = toliqZanjir(
    coin("BTC", [blok(3, 4, { nom: "Fundamental" })]),
  );
  assert.equal(yoyilgan.length, 4);
  assert.equal(yoyilgan[0]?.nom, "Fundamental");
  assert.equal(yoyilgan[3], undefined);
});

// --------------------------------------------------------------------- //
//  Xulosa va indeks
// --------------------------------------------------------------------- //

test("bo'sh ro'yxatda indeks RAQAM emas, null", () => {
  assert.equal(salomatlikIndeksi(xulosaHisobla([])), null);
});

test("hamma coin to'liq bo'lsa indeks 100", () => {
  const toliqCoin = coin(
    "BTC",
    BLOK_NOMLARI.map((nom) => blok(4, 4, { nom })),
    { toliq: true, natija: "signal" },
  );
  assert.equal(
    salomatlikIndeksi(
      xulosaHisobla([toliqCoin, { ...toliqCoin, symbol: "ETH" }]),
    ),
    100,
  );
});

/** Ochiq signali bor coin "zaif" emas — u shunchaki tekshirilmagan.
 *  O'rtachaga kirsa, ochiq signal ko'paygan sari indeks pasayardi
 *  va sabab hech qayerda ko'rinmasdi. */
test("tekshirilmagan coin O'RTACHAGA kirmaydi", () => {
  const toliqCoin = coin(
    "BTC",
    BLOK_NOMLARI.map((nom) => blok(4, 4, { nom })),
    {
      toliq: true,
    },
  );
  const tekshirilmagan = coin("ETH", [], { natija: "ochiq_signal" });

  const xulosa = xulosaHisobla([toliqCoin, tekshirilmagan]);
  assert.equal(xulosa.jami, 1, "tekshirilmagan coin hisobga kirdi");
  assert.equal(salomatlikIndeksi(xulosa), 100);
});

test("uzilish joylari sanaladi", () => {
  const xulosa = xulosaHisobla([
    coin("BTC", [blok(0, 4)], { uzildiBlokda: "Fundamental" }),
    coin("ETH", [blok(0, 4)], { uzildiBlokda: "Fundamental" }),
    coin("SOL", [blok(1, 4)], { uzildiBlokda: "Struktura" }),
  ]);
  assert.equal(xulosa.uzilishlar["Fundamental"], 2);
  assert.equal(xulosa.uzilishlar["Struktura"], 1);
});

test("eng oxirgi tekshiruv vaqti olinadi", () => {
  const xulosa = xulosaHisobla([
    coin("BTC", [blok(4, 4)], {
      tekshirilgan: new Date("2026-09-04T08:00:00Z"),
    }),
    coin("ETH", [blok(4, 4)], {
      tekshirilgan: new Date("2026-09-04T12:00:00Z"),
    }),
  ]);
  assert.equal(xulosa.oxirgi?.toISOString(), "2026-09-04T12:00:00.000Z");
});
