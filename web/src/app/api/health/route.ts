/** Railway sog'liq tekshiruvi (healthcheck).
 *
 * ATAYLAB hech narsaga bog'liq emas: bazaga ham, muhit o'zgaruvchilariga
 * ham tegmaydi. Bu manzil bitta savolga javob beradi — "HTTP server
 * ko'tarildimi?".
 *
 * Nima uchun sahifa (`/kirish`) emas: sahifa cookie o'qiydi, sozlamalarni
 * tekshiradi va nazariy jihatdan 500 qaytarishi mumkin. O'shanda Railway
 * deploy'ni MUVAFFAQIYATSIZ deb belgilaydi va ESKI versiyani saqlab
 * qoladi — natijada tashqaridan "Application failed to respond" ko'rinadi
 * va sabab umuman ko'rinmaydi. Sog'liq tekshiruvi ilovaning ishlashini
 * emas, TIRIKLIGINI o'lchashi kerak.
 */
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  return Response.json({
    ok: true,
    port: process.env.PORT ?? null,
    vaqt: new Date().toISOString(),
  });
}
