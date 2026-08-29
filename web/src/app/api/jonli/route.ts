import { NextResponse } from "next/server";

import { jonliHolat } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Jonli tahlil monitori — sahifa har necha soniyada shu yerdan o'qiydi.
 *
 * FAQAT ADMIN. Bu ichki diagnostika: qaysi coin qaysi bosqichda
 * to'xtayotgani strategiyaning ish usuli haqida ma'lumot beradi.
 * Oddiy foydalanuvchiga u kerak emas va ochiq bo'lmasligi kerak.
 *
 * WebSocket EMAS, oddiy polling. Sabab: sikl har necha daqiqada bir
 * marta ishlaydi, ya'ni yangilanish tezligi baribir sikl tezligi bilan
 * cheklangan. WebSocket bu yerda ulanishni ushlab turish va uzilishni
 * qayta tiklash muammosini qo'shardi, foyda esa bermasdi.
 */
export async function GET(): Promise<NextResponse> {
  const { kirgan, admin } = await kirim();
  if (!kirgan || !admin) {
    return NextResponse.json({ xato: "Ruxsat yo'q" }, { status: 403 });
  }

  return NextResponse.json(jonliHolat(), {
    headers: { "Cache-Control": "private, no-store" },
  });
}
