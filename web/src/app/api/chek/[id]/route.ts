import { NextResponse } from "next/server";

import { env } from "@/lib/env";
import { kutilayotganTolovlar } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** To'lov chekining rasmi — FAQAT ADMIN uchun.
 *
 * NEGA PROKSI KERAK: chek Telegramda `file_id` sifatida yotadi va uni
 * olish uchun BOT TOKENI kerak. Token brauzerga chiqmasligi kerak —
 * u bilan butun botni boshqarish mumkin. Shuning uchun rasmni server
 * o'zi olib beradi.
 *
 * NEGA VIDEODAN FARQLI O'LAROQ BU ISHLAYDI: Bot API `getFile` faqat
 * 20 MB gacha fayl beradi. Video darslik odatda bundan katta (shuning
 * uchun u diskka yuklanadi), chek esa RASM — u har doim bir necha yuz
 * kilobayt.
 *
 * Avval admin har bir to'lovni tasdiqlash uchun Telegramga o'tishi
 * kerak edi: saytda "Chek botda ko'riladi" deb turardi.
 */
export async function GET(
  _sorov: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { admin } = await kirim();
  if (!admin) {
    return NextResponse.json({ xato: "Ruxsat yo'q" }, { status: 403 });
  }

  const { id } = await params;
  // Faqat KUTILAYOTGAN to'lovlar ro'yxatidan: tasdiqlangan yoki rad
  // etilgan to'lovning cheki endi kerak emas va ochiq turmasligi kerak.
  const tolov = kutilayotganTolovlar(200).find((p) => p.id === Number(id));
  if (!tolov?.receiptFileId) {
    return NextResponse.json({ xato: "Chek topilmadi" }, { status: 404 });
  }

  const token = env().botToken;
  try {
    const javob = await fetch(
      `https://api.telegram.org/bot${token}/getFile?file_id=${encodeURIComponent(tolov.receiptFileId)}`,
      { cache: "no-store" },
    );
    const natija = (await javob.json()) as {
      ok: boolean;
      result?: { file_path?: string };
      description?: string;
    };
    if (!natija.ok || !natija.result?.file_path) {
      return NextResponse.json(
        { xato: natija.description ?? "Telegram faylni bermadi" },
        { status: 502 },
      );
    }

    const fayl = await fetch(
      `https://api.telegram.org/file/bot${token}/${natija.result.file_path}`,
      { cache: "no-store" },
    );
    if (!fayl.ok || !fayl.body) {
      return NextResponse.json({ xato: "Fayl yuklanmadi" }, { status: 502 });
    }

    return new Response(fayl.body, {
      status: 200,
      headers: {
        "Content-Type": fayl.headers.get("content-type") ?? "image/jpeg",
        // Keshlanmasin: chek — shaxsiy hujjat, u brauzer keshida
        // qolib ketmasligi kerak.
        "Cache-Control": "private, no-store",
      },
    });
  } catch {
    // Tarmoq uzilsa ham admin paneli ishlayveradi (0.3-band).
    return NextResponse.json({ xato: "Telegramga ulanib bo'lmadi" }, { status: 502 });
  }
}
