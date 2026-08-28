import type { NextRequest } from "next/server";

import { db } from "@/lib/db";
import { MENYU } from "@/lib/menyu";

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
 *
 * `?tekshir=versiya` — SERVERDA QAYSI KOD ISHLAYAPTI. Bu savol bir
 * necha marta soatlab vaqt oldi: yangi kod GitHub'da bor, sayt esa
 * eskisini ko'rsatib turadi va tashqaridan ikkalasi bir xil ko'rinadi.
 * "Deploy o'tdi" degan yozuv yetarli emas — u qaysi COMMIT o'tganini
 * aytmaydi.
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

/** Ishlayotgan kodning shaxsiyati.
 *
 * IKKI XIL MANBA, ataylab:
 *
 *   1. `RAILWAY_GIT_*` — platformaning DA'VOSI: qaysi repo, qaysi shox,
 *      qaysi commit qurildi. Ular ishlash paytida o'qiladi, ya'ni
 *      har doim shu konteynerniki.
 *
 *   2. `menyu` — KODNING O'ZIDAN olingan barmoq izi. Platforma
 *      o'zgaruvchilari yo'q bo'lsa yoki yolg'on aytsa ham, bu ro'yxat
 *      aynan shu qurilishdagi kodni ko'rsatadi: `salomatlik` bandi
 *      bo'lsa — yangi kod, `sokinlik` bo'lsa — eskisi.
 *
 * Da'vo bilan haqiqat ayrilib qolgan holat allaqachon uchragan, shuning
 * uchun ikkalasi ham qaytariladi.
 */
function versiya() {
  return {
    repo: process.env.RAILWAY_GIT_REPO_OWNER
      ? `${process.env.RAILWAY_GIT_REPO_OWNER}/${process.env.RAILWAY_GIT_REPO_NAME}`
      : null,
    shox: process.env.RAILWAY_GIT_BRANCH ?? null,
    commit: process.env.RAILWAY_GIT_COMMIT_SHA ?? null,
    deploy: process.env.RAILWAY_DEPLOYMENT_ID ?? null,
    menyu: MENYU.map((b) => b.kod),
  };
}

export async function GET(request: NextRequest): Promise<Response> {
  const asos = {
    ok: true,
    port: process.env.PORT ?? null,
    vaqt: new Date().toISOString(),
  };
  const tekshir = request.nextUrl.searchParams.get("tekshir");
  if (tekshir === "baza") {
    return Response.json({ ...asos, baza: bazaniTekshir() });
  }
  if (tekshir === "versiya") {
    return Response.json({ ...asos, versiya: versiya() });
  }
  return Response.json(asos);
}
