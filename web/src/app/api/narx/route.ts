import { NextResponse } from "next/server";

import { narxlarniOl } from "@/lib/jonli-server";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Jonli narxlar — signal kartochkasidagi foizni yangilash uchun.
 *
 * KIRISH TEKSHIRILADI: bu ochiq proksi bo'lib qolmasin. Narxning o'zi
 * maxfiy emas, lekin manzilimizni birov o'z sayti uchun bepul narx
 * manbai qilib ishlatishi kerak emas.
 *
 * Narxni SERVER oladi, brauzer emas: foydalanuvchining tarmog'i
 * Binance'ni to'sishi mumkin, Railway'dan esa yo'l ishlashi aniq
 * (bot sham ma'lumotini shu yerdan oladi).
 */
export async function GET(sorov: Request): Promise<NextResponse> {
  const { kirgan } = await kirim();
  if (!kirgan) {
    return NextResponse.json({ xato: "Kirilmagan" }, { status: 403 });
  }

  const xom = new URL(sorov.url).searchParams.get("juftlar") ?? "";
  const juftlar = xom
    .split(",")
    .map((j) => j.trim().toUpperCase())
    .filter((j) => /^[A-Z0-9]{4,24}$/.test(j))
    .slice(0, 30);

  const narxlar = await narxlarniOl(juftlar);
  return NextResponse.json(
    { narxlar },
    { headers: { "Cache-Control": "private, no-store" } },
  );
}
