import { type NextRequest, NextResponse } from "next/server";

import { TIL_COOKIE, tilmi } from "@/lib/i18n";

/** Til almashtirish. Tanlov bir yil saqlanadi. */
export async function POST(request: NextRequest) {
  const forma = await request.formData();
  const til = String(forma.get("til") ?? "");
  const qayerga = String(forma.get("qayerga") ?? "/bosh");

  // Ochiq yo'naltirishning oldini olamiz: faqat shu saytdagi yo'l
  const xavfsizYol = qayerga.startsWith("/") && !qayerga.startsWith("//") ? qayerga : "/bosh";

  const javob = NextResponse.redirect(new URL(xavfsizYol, request.url), { status: 303 });
  if (tilmi(til)) {
    javob.cookies.set(TIL_COOKIE, til, { path: "/", maxAge: 365 * 24 * 60 * 60, sameSite: "lax" });
  }
  return javob;
}
