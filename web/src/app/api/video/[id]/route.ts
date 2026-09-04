import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { Readable } from "node:stream";

import { NextResponse } from "next/server";

import { MediaXatosi, mimeTuri, oraliqniOqi, videoYoli } from "@/lib/media";
import { dars, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Video darslikni berish — obunachi uchun, oqim (streaming) bilan.
 *
 * NEGA FAYL TO'G'RIDAN-TO'G'RI OCHIQ TURMAYDI: agar video oddiy statik
 * fayl bo'lsa, uning manzilini bilgan HAR KIM ko'ra olardi — obuna
 * tekshiruvi chetlab o'tilardi. Shuning uchun har bir so'rov shu
 * yerdan o'tadi va tarif tekshiriladi.
 *
 * NEGA `Range` KERAK: usiz brauzer videoni faqat boshidan oxirigacha
 * ketma-ket yuklaydi — o'rtaga sakrash (seek) ishlamaydi va uzun
 * darsda bu darrov seziladi. `Accept-Ranges` va 206 javobi shuni
 * ochadi.
 */
export async function GET(
  sorov: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse | Response> {
  const { tarif } = await kirim();
  const { id } = await params;

  const dars_ = dars(Number(id));
  if (!dars_ || !dars_.videoPath || !dars_.published) {
    return NextResponse.json({ xato: "Topilmadi" }, { status: 404 });
  }
  if (!tarifQamraydi(tarif, dars_.minTier)) {
    return NextResponse.json({ xato: "Obuna yetarli emas" }, { status: 403 });
  }

  let yol: string;
  try {
    yol = videoYoli(dars_.videoPath);
  } catch (xato) {
    if (xato instanceof MediaXatosi) {
      return NextResponse.json({ xato: "Topilmadi" }, { status: 404 });
    }
    throw xato;
  }

  let hajm: number;
  try {
    hajm = (await stat(yol)).size;
  } catch {
    // Bazada yozuv bor, fayl esa yo'q — disk almashgan yoki qo'lda
    // o'chirilgan. 404 aniqroq: 500 "sayt buzuq" degan taassurot beradi.
    return NextResponse.json(
      { xato: "Fayl diskda topilmadi" },
      { status: 404 },
    );
  }

  const turi = mimeTuri(dars_.videoPath);
  const sarlavhalar: Record<string, string> = {
    "Content-Type": turi,
    "Accept-Ranges": "bytes",
    // Keshlanmasin: obuna tugagach eski javob qaytib qolmasin.
    "Cache-Control": "private, no-store",
  };

  const oraliq = oraliqniOqi(sorov.headers.get("range"), hajm);
  if (oraliq === "yaroqsiz") {
    return new Response(null, {
      status: 416,
      headers: { "Content-Range": `bytes */${hajm}` },
    });
  }

  if (oraliq === null) {
    const oqim = Readable.toWeb(createReadStream(yol)) as ReadableStream;
    return new Response(oqim, {
      status: 200,
      headers: { ...sarlavhalar, "Content-Length": String(hajm) },
    });
  }

  const { boshi, oxiri } = oraliq;
  const oqim = Readable.toWeb(
    createReadStream(yol, { start: boshi, end: oxiri }),
  ) as ReadableStream;
  return new Response(oqim, {
    status: 206,
    headers: {
      ...sarlavhalar,
      "Content-Range": `bytes ${boshi}-${oxiri}/${hajm}`,
      "Content-Length": String(oxiri - boshi + 1),
    },
  });
}
