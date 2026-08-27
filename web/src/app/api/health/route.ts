import type { NextRequest } from "next/server";

import { db } from "@/lib/db";

/** Railway sog'liq tekshiruvi va tashxis.
 *
 * Oddiy holatda ATAYLAB hech narsaga bog'liq emas: bazaga ham, muhit
 * o'zgaruvchilariga ham tegmaydi. Bitta savolga javob beradi — "HTTP
 * server ko'tarildimi?".
 *
 * `?tekshir=baza` — alohida tashxis: bazani ochib ko'radi va xatoni
 * MATN sifatida qaytaradi. Nima uchun kerak bo'ldi: serverda bazaga
 * tegadigan har qanday so'rov 502 qaytardi, ya'ni jarayon o'ldi. O'lgan
 * jarayon esa xato xabarini yozib ulgurmaydi — na ekranda, na logda hech
 * narsa qolmaydi.
 */
export const dynamic = "force-dynamic";

type Natija = { holat: "ok"; foydalanuvchilar: number } | { holat: "xato"; xabar: string };

function bazaniTekshir(): Natija {
  try {
    // Ilovaning HAQIQIY yo'li tekshiriladi. Alohida ulanish qursak, u
    // ishlab, ilovaniki ishlamasligi mumkin edi va tashxis yolg'on
    // tinchlik berardi.
    const qator = db().prepare("select count(*) as n from users").get() as { n: number };
    return { holat: "ok", foydalanuvchilar: Number(qator.n) };
  } catch (e) {
    return { holat: "xato", xabar: e instanceof Error ? `${e.name}: ${e.message}` : String(e) };
  }
}

export async function GET(request: NextRequest): Promise<Response> {
  const asos = {
    ok: true,
    port: process.env.PORT ?? null,
    vaqt: new Date().toISOString(),
  };
  if (request.nextUrl.searchParams.get("tekshir") !== "baza") {
    return Response.json(asos);
  }
  return Response.json({ ...asos, baza: bazaniTekshir() });
}
