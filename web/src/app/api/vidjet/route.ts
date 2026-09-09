import type { NextRequest } from "next/server";

import { vidjetTanloviSaqla } from "@/lib/queries";
import { kirim } from "@/lib/session";
import { VIDJETLAR } from "@/lib/vidjetlar";

/** Vidjet tanlovini saqlaydi.
 *
 * KODLAR RO'YXATGA SOLISHTIRILADI. So'rovni qo'lda yuborish mumkin
 * va u yerga istalgan matn yozilishi mumkin. Tekshirilmasa, bazaga
 * hech qachon chizilmaydigan kod tushib qolardi va u yerda abadiy
 * yotardi.
 *
 * TAKRORLANGANLARI TASHLANADI: bitta vidjet ikki marta yuborilsa,
 * baza `uq_widget_user_widget` cheklovida yiqilardi. Xato o'rniga
 * jimgina tozalaymiz — bu foydalanuvchining aybi emas.
 */
export async function POST(request: NextRequest) {
  const { kirgan, foydalanuvchi } = await kirim();
  if (!kirgan || !foydalanuvchi) {
    return Response.json({ ok: false }, { status: 401 });
  }

  let tana: unknown;
  try {
    tana = await request.json();
  } catch {
    return Response.json({ ok: false }, { status: 400 });
  }

  const kelgan = (tana as { vidjetlar?: unknown }).vidjetlar;
  if (!Array.isArray(kelgan)) {
    return Response.json({ ok: false }, { status: 400 });
  }

  const maqbul = new Set(VIDJETLAR.map((v) => v.kod));
  const korgan = new Set<string>();
  const tozalangan: string[] = [];
  for (const x of kelgan) {
    if (typeof x !== "string" || !maqbul.has(x as never)) continue;
    if (korgan.has(x)) continue;
    korgan.add(x);
    tozalangan.push(x);
  }

  const natija = vidjetTanloviSaqla(foydalanuvchi.id, tozalangan);
  return Response.json(natija, { status: natija.ok ? 200 : 400 });
}
