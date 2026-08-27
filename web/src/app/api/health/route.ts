import type { NextRequest } from "next/server";

/** Railway sog'liq tekshiruvi va tashxis.
 *
 * Oddiy holatda ATAYLAB hech narsaga bog'liq emas: bazaga ham, muhit
 * o'zgaruvchilariga ham tegmaydi. Bu manzil bitta savolga javob beradi —
 * "HTTP server ko'tarildimi?".
 *
 * `?tekshir=baza` — alohida tashxis. Nima uchun kerak bo'ldi: serverda
 * bazaga tegadigan har qanday so'rov 502 qaytardi, ya'ni JARAYON O'LDI.
 * O'lgan jarayon esa xato xabarini yozib ulgurmaydi — na ekranda, na
 * logda hech narsa qolmaydi. Bu manzil o'sha xatoni TUTIB, matn sifatida
 * qaytaradi.
 */
export const dynamic = "force-dynamic";

type Natija = { holat: "ok" } | { holat: "xato"; bosqich: string; xabar: string };

async function bazaniTekshir(): Promise<Natija> {
  // Dinamik import: `better-sqlite3` — mahalliy (native) modul. U yuklanish
  // paytining O'ZIDA yiqilishi mumkin, tepadagi oddiy `import` esa bunday
  // xatoni tutib bo'lmaydigan joyga qo'yardi.
  let Database: typeof import("better-sqlite3");
  try {
    Database = (await import("better-sqlite3")).default as unknown as typeof import(
      "better-sqlite3"
    );
  } catch (e) {
    return { holat: "xato", bosqich: "modul yuklash", xabar: String(e) };
  }

  let yol: string;
  try {
    const { bazaYoli } = await import("@/lib/env");
    yol = bazaYoli();
  } catch (e) {
    return { holat: "xato", bosqich: "yo'lni aniqlash", xabar: String(e) };
  }

  try {
    // Faqat O'QISH uchun ochamiz: tekshiruv hech narsani o'zgartirmasin.
    const baza = new (Database as unknown as new (
      p: string,
      o?: Record<string, unknown>,
    ) => { prepare: (s: string) => { get: () => unknown }; close: () => void })(yol, {
      readonly: true,
      fileMustExist: true,
    });
    baza.prepare("select count(*) as n from users").get();
    baza.close();
    return { holat: "ok" };
  } catch (e) {
    return { holat: "xato", bosqich: `ochish (${yol})`, xabar: String(e) };
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
  return Response.json({ ...asos, baza: await bazaniTekshir() });
}
