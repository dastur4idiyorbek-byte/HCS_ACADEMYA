import type { NextRequest } from "next/server";

import { ilgarilashSaqla, kontent, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

/** O'qish/ko'rish holatini yozadi.
 *
 * IKKITA TEKSHIRUV SERVERDA, chunki so'rovni istalgan kishi qo'lda
 * yuborishi mumkin:
 *
 *   1. Foydalanuvchi KIRGANMI — aks holda kimning holati ekani
 *      noma'lum.
 *   2. Shu darsga TARIFI YETADIMI — aks holda qulflangan darsni
 *      "o'qidim" deb belgilab, uni "Davom ettirish" kartochkasiga
 *      chiqarib olish mumkin bo'lardi.
 *
 * Foizni faqat OLDINGA suradi — bu qoida `ilgarilashSaqla` ichida.
 */
export async function POST(request: NextRequest) {
  const { kirgan, tarif, foydalanuvchi } = await kirim();
  if (!kirgan || !foydalanuvchi) {
    return Response.json({ ok: false }, { status: 401 });
  }

  let tana: unknown;
  try {
    tana = await request.json();
  } catch {
    return Response.json({ ok: false }, { status: 400 });
  }

  const q = tana as { kontentId?: unknown; foiz?: unknown };
  const kontentId = Number(q.kontentId);
  const foiz = Number(q.foiz);
  if (!Number.isInteger(kontentId) || !Number.isFinite(foiz)) {
    return Response.json({ ok: false }, { status: 400 });
  }

  const dars = kontent().find((k) => k.id === kontentId);
  if (!dars || !tarifQamraydi(tarif, dars.minTier)) {
    return Response.json({ ok: false }, { status: 403 });
  }

  const natija = ilgarilashSaqla(foydalanuvchi.id, kontentId, foiz);
  return Response.json(natija, { status: natija.ok ? 200 : 400 });
}
