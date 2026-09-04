import { stat } from "node:fs/promises";
import { createReadStream } from "node:fs";
import { Readable } from "node:stream";

import { NextResponse } from "next/server";

import { MediaXatosi, postMimeTuri, postYoli } from "@/lib/media";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Bosh sahifa postining rasm/audio fayli.
 *
 * KIRISH TEKSHIRILADI. Bosh sahifa oqimi obunasiz ham ko'rinadi
 * (tanishtiruv sahifasi), lekin fayl manzili ochiq proksi bo'lib
 * qolmasligi kerak — birov uni o'z sayti uchun bepul fayl saqlagich
 * qilib ishlatmasin.
 *
 * Fayl nomi so'rovdan keladi, shuning uchun `postYoli` ikki qavatli
 * tekshiruvdan o'tkazadi: `../../etc/passwd` kabi nom butun serverni
 * ochib qo'yardi.
 */
export async function GET(
  _sorov: Request,
  { params }: { params: Promise<{ nom: string }> },
): Promise<Response> {
  const { kirgan } = await kirim();
  if (!kirgan) {
    return NextResponse.json({ xato: "Kirilmagan" }, { status: 403 });
  }

  const { nom } = await params;
  let yol: string;
  try {
    yol = postYoli(nom);
  } catch (xato) {
    const matn =
      xato instanceof MediaXatosi ? xato.message : "Fayl nomi noto'g'ri";
    return NextResponse.json({ xato: matn }, { status: 400 });
  }

  let hajm: number;
  try {
    hajm = (await stat(yol)).size;
  } catch {
    return NextResponse.json({ xato: "Fayl topilmadi" }, { status: 404 });
  }

  const oqim = Readable.toWeb(createReadStream(yol)) as ReadableStream;
  return new Response(oqim, {
    headers: {
      "Content-Type": postMimeTuri(nom),
      "Content-Length": String(hajm),
      // Fayl nomi takrorlanmaydi (UUID), shuning uchun uzoq keshlash
      // xavfsiz: nomi o'zgarmasa, tarkibi ham o'zgarmaydi.
      "Cache-Control": "private, max-age=31536000, immutable",
    },
  });
}
