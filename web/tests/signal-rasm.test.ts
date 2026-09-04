import assert from "node:assert/strict";
import path from "node:path";
import { test } from "node:test";

import {
  MediaXatosi,
  signalJildi,
  signalMimeTuri,
  signalRasmYoli,
  signalYangiNom,
} from "../src/lib/media.ts";

/** Signal grafiklari (4-prompt, 4-qism).
 *
 * Fayl nomi bazadan keladi, lekin u bir vaqtlar SO'ROVDAN kelgan.
 * `../../etc/passwd` kabi nom butun serverni ochib qo'yardi. */

test("jild nomi bot bilan BIR XIL", () => {
  // Pythondagi nusxasi: `bot/hosting.py` -> `signal_media_dir()`,
  // `tests/bot/test_video_dir.py` shu qiymatni kutadi.
  assert.equal(path.basename(signalJildi()), "signal-media");
});

test("jilddan chiqishga urinish RAD ETILADI", () => {
  for (const yomon of ["../hcs.db", "a/b.png", "a\\b.png", "..", ""]) {
    assert.throws(
      () => signalRasmYoli(yomon),
      MediaXatosi,
      `o'tkazib yuborildi: ${yomon}`,
    );
  }
});

test("oddiy nom qabul qilinadi", () => {
  const yol = signalRasmYoli("a1b2c3.png");
  assert.ok(yol.startsWith(signalJildi() + "/"));
});

/** Signal grafigi — FAQAT RASM. Audio yoki video bu yerda ma'nosiz
 *  va katta fayl kartochkani sekinlashtirardi. */
test("rasm bo'lmagan tur RAD ETILADI", () => {
  for (const yomon of ["ovoz.mp3", "kino.mp4", "hujjat.pdf", "skript.js"]) {
    assert.throws(
      () => signalYangiNom(yomon),
      MediaXatosi,
      `o'tkazib yuborildi: ${yomon}`,
    );
  }
});

test("rasm turlari qabul qilinadi va kengaytma SAQLANADI", () => {
  for (const yaxshi of ["grafik.PNG", "chart.jpg", "x.jpeg", "y.webp"]) {
    const nom = signalYangiNom(yaxshi, "sinov");
    assert.equal(nom, "sinov" + path.extname(yaxshi).toLowerCase());
  }
});

test("mime turi kengaytmadan aniqlanadi", () => {
  assert.equal(signalMimeTuri("a.png"), "image/png");
  assert.equal(signalMimeTuri("a.jpg"), "image/jpeg");
  assert.equal(signalMimeTuri("a.nomalum"), "application/octet-stream");
});
