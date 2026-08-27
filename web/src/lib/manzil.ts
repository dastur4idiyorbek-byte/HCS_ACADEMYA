import { NextResponse } from "next/server";

/** Boshqa sahifaga yo'naltirish — NISBIY manzil bilan.
 *
 * MUAMMO: `NextResponse.redirect(new URL("/bosh", request.url))` manzilni
 * so'rov kelgan domendan emas, serverning BOG'LANISH manzilidan quradi.
 * Railway'da server `0.0.0.0` da tinglaydi, ya'ni brauzerga
 * `https://0.0.0.0:8080/bosh` yuboriladi — bunday manzilga hech kim bora
 * olmaydi. Tashqaridan bu "sayt buzuq" bo'lib ko'rinadi, holbuki sahifalar
 * ishlab turibdi.
 *
 * YECHIM: nisbiy manzil. Brauzer uni o'zi turgan domenga nisbatan
 * hisoblaydi, ya'ni domen, port va protokolni umuman bilishimiz shart
 * emas. `x-forwarded-host` sarlavhasiga tayanish ham mumkin edi, lekin u
 * proksi sozlamasiga bog'liq bo'lardi — bu esa yana bir "sozlanmasa
 * jimgina buziladigan" joy demakdir.
 *
 * 303 (See Other) ishlatiladi: POST dan keyin brauzer GET bilan borishi
 * kerak. GET so'rovlar uchun ham xavfsiz.
 */
export function yonaltir(yol: string, status: 303 | 307 = 303): NextResponse {
  return new NextResponse(null, { status, headers: { Location: yol } });
}
