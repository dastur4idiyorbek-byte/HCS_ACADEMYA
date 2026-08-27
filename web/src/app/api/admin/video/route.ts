import { createWriteStream } from "node:fs";
import { mkdir, unlink } from "node:fs/promises";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";

import { NextResponse } from "next/server";

import {
  MediaXatosi,
  engKattaHajm,
  videoJildi,
  videoYoli,
  yangiNom,
} from "@/lib/media";
import { videoBiriktir } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Video darslikni saytga yuklash — faqat admin.
 *
 * NEGA `multipart/form-data` EMAS, XOM TANA: multipart butun faylni
 * xotiraga yig'adi (yoki uni qo'lda ajratish kerak bo'ladi). Yuz
 * megabaytlik dars uchun bu — yuz megabayt operativ xotira. Bu yerda
 * so'rov tanasining O'ZI fayl: u to'g'ridan-to'g'ri diskka OQIZILADI,
 * xotirada bir vaqtda faqat kichik bo'lak turadi.
 *
 * Fayl nomi `?nom=` da keladi — undan faqat KENGAYTMA olinadi, nomning
 * o'zi tashlanadi.
 *
 * Hajm chegarasi ikki joyda tekshiriladi: sarlavhadagi da'vo
 * (`content-length`) VA haqiqatda oqib kelgan baytlar. Birinchisi
 * yolg'on bo'lishi mumkin, ikkinchisi — bo'lmaydi.
 */
export async function POST(sorov: Request): Promise<NextResponse> {
  const { admin } = await kirim();
  if (!admin) {
    return NextResponse.json({ xato: "Ruxsat yo'q" }, { status: 403 });
  }

  const url = new URL(sorov.url);
  const darsId = Number(url.searchParams.get("dars"));
  const aslNom = url.searchParams.get("nom") ?? "";
  if (!Number.isInteger(darsId) || darsId <= 0) {
    return NextResponse.json({ xato: "Dars raqami noto'g'ri" }, { status: 400 });
  }

  const chegara = engKattaHajm();
  const dagvo = Number(sorov.headers.get("content-length") ?? 0);
  if (dagvo > chegara) {
    return NextResponse.json(
      { xato: `Fayl juda katta: ${(dagvo / 1024 / 1024).toFixed(0)} MB` },
      { status: 413 },
    );
  }

  let nom: string;
  try {
    nom = yangiNom(aslNom);
  } catch (xato) {
    if (xato instanceof MediaXatosi) {
      return NextResponse.json({ xato: xato.message }, { status: 415 });
    }
    throw xato;
  }

  if (!sorov.body) {
    return NextResponse.json({ xato: "Fayl bo'sh" }, { status: 400 });
  }

  await mkdir(videoJildi(), { recursive: true });
  const toliqYol = videoYoli(nom);

  let baytlar = 0;
  const hisoblagich = new TransformStream<Uint8Array, Uint8Array>({
    transform(bolak, boshqaruv) {
      baytlar += bolak.byteLength;
      if (baytlar > chegara) {
        throw new MediaXatosi(
          `Fayl chegaradan katta (${(chegara / 1024 / 1024).toFixed(0)} MB)`,
        );
      }
      boshqaruv.enqueue(bolak);
    },
  });

  try {
    await pipeline(
      Readable.fromWeb(sorov.body.pipeThrough(hisoblagich) as never),
      createWriteStream(toliqYol),
    );
  } catch (xato) {
    // Yarim yozilgan fayl QOLDIRILMAYDI: u diskda joy egallaydi va
    // hech qachon o'ynatilmaydi.
    await unlink(toliqYol).catch(() => {});
    const xabar = xato instanceof MediaXatosi ? xato.message : "Yuklash uzildi";
    return NextResponse.json({ xato: xabar }, { status: 400 });
  }

  // Avval BAZA, keyin eski faylni o'chirish. Teskarisi bo'lsa yozuv
  // yiqilganda dars videosiz qolardi.
  const natija = videoBiriktir(darsId, nom);
  if (!natija.ok) {
    await unlink(toliqYol).catch(() => {});
    return NextResponse.json({ xato: "Bunday dars yo'q" }, { status: 404 });
  }
  if (natija.eskiNom) {
    await unlink(videoYoli(natija.eskiNom)).catch(() => {});
  }

  return NextResponse.json({ ok: true, nom, hajm: baytlar });
}
