import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

import { KITOB_FAYLI, KITOB_TARIFI } from "@/lib/kitob";
import { tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Kitobni yuklab berish — obunaga qarab.
 *
 * NEGA `public/` DA TURMAYDI. `web/public/` ichidagi har qanday fayl
 * manzilini bilgan HAR KIMGA ochiq bo'ladi — obuna tekshiruvi
 * chetlab o'tilardi. Video darsliklar ham aynan shu sababdan shunday
 * beriladi (`api/video/[id]`), va kitob undan farq qilmasligi kerak.
 *
 * Fayl `web/kitob/` da — Next uni statik tarqatmaydi, faqat shu
 * yerdan o'qiladi.
 */
export async function GET(): Promise<NextResponse> {
  const { tarif } = await kirim();
  if (!tarifQamraydi(tarif, KITOB_TARIFI)) {
    return NextResponse.json({ xato: "Obuna yetarli emas" }, { status: 403 });
  }

  let tana: Buffer;
  try {
    tana = await readFile(path.join(process.cwd(), "kitob", KITOB_FAYLI));
  } catch {
    // Fayl yo'q — `python -m scripts.kitob.qur` yugurtirilmagan.
    // 404 aniqroq: 500 "sayt buzuq" degan taassurot berardi.
    return NextResponse.json({ xato: "Kitob hali tayyor emas" }, { status: 404 });
  }

  return new NextResponse(new Uint8Array(tana), {
    headers: {
      "content-type": "application/pdf",
      "content-disposition": `attachment; filename="${KITOB_FAYLI}"`,
      "content-length": String(tana.length),
      // Kitob har deployda qayta quriladi — keshda eskisi qolmasin.
      "cache-control": "private, no-store",
    },
  });
}
