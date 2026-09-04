import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { Readable } from "node:stream";

import { NextResponse } from "next/server";

import { MediaXatosi, signalMimeTuri, signalRasmYoli } from "@/lib/media";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Signal grafigining rasmi.
 *
 * OBUNA TEKSHIRILADI, kirish emas. Grafik signalning bir qismi —
 * u kirish, Stop va TP darajalarini ko'rsatadi, ya'ni bu bizning
 * MAHSULOTIMIZ. Obunasiz odam signal kartochkasini ko'ra olmaydi,
 * demak uning rasmini ham ko'rmasligi kerak: aks holda rasm manzili
 * himoyani chetlab o'tadigan teshik bo'lardi.
 */
export async function GET(
  _sorov: Request,
  { params }: { params: Promise<{ nom: string }> },
): Promise<Response> {
  const { tarif } = await kirim();
  const { tarifQamraydi } = await import("@/lib/queries");
  if (!tarifQamraydi(tarif, "lite")) {
    return NextResponse.json({ xato: "Obuna kerak" }, { status: 403 });
  }

  const { nom } = await params;
  let yol: string;
  try {
    yol = signalRasmYoli(nom);
  } catch (xato) {
    const matn =
      xato instanceof MediaXatosi ? xato.message : "Fayl nomi noto'g'ri";
    return NextResponse.json({ xato: matn }, { status: 400 });
  }

  let hajm: number;
  try {
    hajm = (await stat(yol)).size;
  } catch {
    return NextResponse.json({ xato: "Rasm topilmadi" }, { status: 404 });
  }

  const oqim = Readable.toWeb(createReadStream(yol)) as ReadableStream;
  return new Response(oqim, {
    headers: {
      "Content-Type": signalMimeTuri(nom),
      "Content-Length": String(hajm),
      "Cache-Control": "private, max-age=31536000, immutable",
    },
  });
}
