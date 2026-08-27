import { type NextRequest, NextResponse } from "next/server";

import { SESSIYA_COOKIE } from "@/lib/auth";

/** Chiqish — faqat POST.
 *
 * GET bo'lsa, boshqa saytdagi `<img src="/api/auth/chiqish">` ham
 * foydalanuvchini chiqarib yuborishi mumkin edi.
 */
export async function POST(request: NextRequest) {
  const javob = NextResponse.redirect(new URL("/kirish", request.url), { status: 303 });
  javob.cookies.set(SESSIYA_COOKIE, "", { path: "/", maxAge: 0 });
  return javob;
}
