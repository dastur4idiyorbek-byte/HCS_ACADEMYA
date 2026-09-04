import { mkdir, writeFile } from "node:fs/promises";

import { NextResponse } from "next/server";

import {
  MediaXatosi,
  postEngKattaHajm,
  postJildi,
  postYangiNom,
  postYoli,
} from "@/lib/media";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Bosh sahifa posti uchun rasm/audio yuklash — faqat admin.
 *
 * NEGA VIDEODAN SODDAROQ: video yuz megabaytlik bo'lgani uchun oqim
 * bilan yoziladi. Post fayli 25 MB gacha — uni bir yo'la o'qish
 * xavfsiz va kod ancha qisqa.
 *
 * Fayl nomi `?nom=` da keladi, undan faqat KENGAYTMA olinadi:
 * asl nomda bo'sh joy, kirill harf yoki xavfli belgi bo'lishi mumkin.
 *
 * Hajm IKKI joyda tekshiriladi — sarlavhadagi da'vo yolg'on bo'lishi
 * mumkin, haqiqatda kelgan baytlar esa yo'q.
 */
export async function POST(sorov: Request): Promise<NextResponse> {
  const { admin } = await kirim();
  if (!admin) {
    return NextResponse.json({ xato: "Ruxsat yo'q" }, { status: 403 });
  }

  const aslNom = new URL(sorov.url).searchParams.get("nom") ?? "";
  const chegara = postEngKattaHajm();
  const dagvo = Number(sorov.headers.get("content-length") ?? 0);
  if (dagvo > chegara) {
    return NextResponse.json(
      { xato: `Fayl juda katta: ${(dagvo / 1024 / 1024).toFixed(1)} MB` },
      { status: 413 },
    );
  }

  let nom: string;
  try {
    nom = postYangiNom(aslNom);
  } catch (xato) {
    const matn =
      xato instanceof MediaXatosi ? xato.message : "Fayl turi noto'g'ri";
    return NextResponse.json({ xato: matn }, { status: 400 });
  }

  const tana = new Uint8Array(await sorov.arrayBuffer());
  if (tana.byteLength === 0) {
    return NextResponse.json({ xato: "Fayl bo'sh" }, { status: 400 });
  }
  if (tana.byteLength > chegara) {
    return NextResponse.json(
      {
        xato: `Fayl juda katta: ${(tana.byteLength / 1024 / 1024).toFixed(1)} MB`,
      },
      { status: 413 },
    );
  }

  await mkdir(postJildi(), { recursive: true });
  await writeFile(postYoli(nom), tana);

  // Post yozuvi ALOHIDA qadamda yaratiladi (formani yuborishda).
  // Nima uchun: admin faylni yuklab, keyin matnni o'ylab, keyin
  // "nashr et" bosishi mumkin. Fayl darrov postga aylansa, yarim
  // tayyor post oqimda paydo bo'lardi.
  return NextResponse.json({ nom });
}
