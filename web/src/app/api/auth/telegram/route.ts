import type { NextRequest } from "next/server";

import { SESSIYA_COOKIE, SESSIYA_SEK, sessiyaYarat, telegramLoginTekshir } from "@/lib/auth";
import { env } from "@/lib/env";
import { yonaltir } from "@/lib/manzil";
import { foydalanuvchiniYozib } from "@/lib/queries";

/** Telegram Login Widget shu manzilga QAYTARADI (redirect rejimi).
 *
 * XAVFSIZLIK: bu yerga kelgan so'rov Telegramdan emas, BRAUZERDAN keladi.
 * Ya'ni istalgan odam `?id=<admin_id>` deb yozib yuborishi mumkin.
 * `telegramLoginTekshir` — yagona to'siq: u `hash` ni bot tokeni bilan
 * qayta hisoblab solishtiradi. Shu qadamsiz butun sayt ochiq eshik.
 */
export async function GET(request: NextRequest) {
  const params = Object.fromEntries(request.nextUrl.searchParams.entries());
  const { botToken, adminIds } = env();

  const login = telegramLoginTekshir(params, botToken);
  if (!login) {
    // Sabab AYTILMAYDI (imzo xatomi, eskirganmi) — bu hujumchiga
    // foydali ma'lumot bo'lardi. Foydalanuvchi uchun natija bir xil.
    return yonaltir("/kirish?xato=1");
  }

  const toliqIsm = [login.first_name, login.last_name].filter(Boolean).join(" ") || null;
  foydalanuvchiniYozib(login.id, login.username ?? null, toliqIsm, adminIds.has(login.id));

  const { token } = sessiyaYarat(login.id, botToken);
  const javob = yonaltir("/bosh");
  javob.cookies.set(SESSIYA_COOKIE, token, {
    httpOnly: true,       // JavaScript o'qiy olmasin (XSS bo'lsa ham)
    sameSite: "lax",      // boshqa saytdan yuborilgan so'rovda kelmasin
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSIYA_SEK,  // 144 soat — topshiriq 2-bo'limi
  });
  return javob;
}
