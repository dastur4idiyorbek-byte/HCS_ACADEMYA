import { SESSIYA_COOKIE } from "@/lib/auth";
import { yonaltir } from "@/lib/manzil";

/** Chiqish — faqat POST.
 *
 * GET bo'lsa, boshqa saytdagi `<img src="/api/auth/chiqish">` ham
 * foydalanuvchini chiqarib yuborishi mumkin edi.
 */
export async function POST() {
  const javob = yonaltir("/kirish");
  javob.cookies.set(SESSIYA_COOKIE, "", { path: "/", maxAge: 0 });
  return javob;
}
