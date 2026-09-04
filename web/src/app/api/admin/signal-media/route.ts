import { mkdir, writeFile } from "node:fs/promises";

import { NextResponse } from "next/server";

import {
  MediaXatosi,
  signalEngKattaHajm,
  signalJildi,
  signalRasmYoli,
  signalYangiNom,
} from "@/lib/media";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Signal grafigini yuklash — faqat admin (4-prompt, 4-qism).
 *
 * Rasm admin TradingView'da CHIZIB, skrinshot qilib yuklaydi.
 * Tizim o'zi ham grafik chizadi (Pillow), lekin u faqat darajalarni
 * ko'rsatadi; qo'lda chizilgan rasm esa STRUKTURANI — nega aynan shu
 * joy tanlangani. Ikkalasi boshqa savolga javob beradi.
 *
 * Fayl yozuvi ALOHIDA qadamda signalga biriktiriladi: admin rasmni
 * yuklab, keyin qaysi maydonga (kirish yoki natija) qo'yishni
 * tanlaydi.
 */
export async function POST(sorov: Request): Promise<NextResponse> {
  const { admin } = await kirim();
  if (!admin) {
    return NextResponse.json({ xato: "Ruxsat yo'q" }, { status: 403 });
  }

  const aslNom = new URL(sorov.url).searchParams.get("nom") ?? "";
  const chegara = signalEngKattaHajm();
  const dagvo = Number(sorov.headers.get("content-length") ?? 0);
  if (dagvo > chegara) {
    return NextResponse.json(
      { xato: `Rasm juda katta: ${(dagvo / 1024 / 1024).toFixed(1)} MB` },
      { status: 413 },
    );
  }

  let nom: string;
  try {
    nom = signalYangiNom(aslNom);
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
        xato: `Rasm juda katta: ${(tana.byteLength / 1024 / 1024).toFixed(1)} MB`,
      },
      { status: 413 },
    );
  }

  await mkdir(signalJildi(), { recursive: true });
  await writeFile(signalRasmYoli(nom), tana);
  return NextResponse.json({ nom });
}
