import { sozlama } from "./config.ts";

/** Jonli narxlarni BINANCE'DAN olish — faqat SERVER.
 *
 * NEGA ALOHIDA FAYL: bu modul `config.ts` orqali `node:fs` ni tortadi.
 * Sof foiz hisobi (`jonli.ts`) esa brauzerda ham kerak. Ikkalasi bitta
 * faylda turganda `next build` yiqildi:
 *
 *     the chunking context does not support external modules
 *     (request: node:fs)
 *
 * Ya'ni klient to'plamiga fayl tizimi kirib ketardi. Chegara shu
 * yerda: `jonli.ts` — hamma joyda, `jonli-server.ts` — faqat serverda.
 *
 * NEGA BROWZER TO'G'RIDAN-TO'G'RI BINANCE'GA MUROJAAT QILMAYDI:
 * foydalanuvchining tarmog'i Binance'ni to'sishi mumkin va o'shanda
 * foiz hech kimda ko'rinmasdi. Railway'dan Binance'ga yo'l esa
 * ISHLASHI ANIQ — bot shu yerdan sham ma'lumotini oladi.
 *
 * Kesh ham shu sababdan serverda: yuzta obunachi sahifani ochsa,
 * Binance'ga yuzta emas, bir nechta so'rov ketadi.
 */

type Kesh = { narxlar: Record<string, number>; vaqt: number };

/** Kesh muddati. Qisqa — narx jonli bo'lishi kerak; lekin nol emas,
 *  aks holda har sahifa ochilishi Binance'ga so'rov bo'lardi. */
export const KESH_MS = 15_000;

let kesh: Kesh = { narxlar: {}, vaqt: 0 };

/** Binance'dan bir nechta juftlik narxini bitta so'rovda oladi.
 *
 * HECH QACHON ISTISNO TASHLAMAYDI (0.3-band): narx — qo'shimcha
 * ma'lumot, signalning o'zi emas. Binance javob bermasa bo'sh obyekt
 * qaytadi va sahifada foiz ko'rsatilmaydi, xolos.
 */
export async function narxlarniOl(juftlar: string[]): Promise<Record<string, number>> {
  const kerak = [...new Set(juftlar.map((j) => j.toUpperCase()))].filter(Boolean);
  if (kerak.length === 0) return {};

  const hozir = Date.now();
  if (hozir - kesh.vaqt < KESH_MS && kerak.every((j) => j in kesh.narxlar)) {
    return Object.fromEntries(kerak.map((j) => [j, kesh.narxlar[j]]));
  }

  const asos = sozlama<string>(["market_data", "rest_base_url"], "https://api.binance.com");
  const manzil =
    `${asos}/api/v3/ticker/price?symbols=` +
    encodeURIComponent(JSON.stringify(kerak));

  try {
    const javob = await fetch(manzil, {
      cache: "no-store",
      signal: AbortSignal.timeout(6000),
    });
    if (!javob.ok) return kesh.narxlar;

    const xom = (await javob.json()) as { symbol: string; price: string }[];
    const yangi: Record<string, number> = { ...kesh.narxlar };
    for (const q of Array.isArray(xom) ? xom : []) {
      const son = Number(q.price);
      if (Number.isFinite(son) && son > 0) yangi[q.symbol.toUpperCase()] = son;
    }
    kesh = { narxlar: yangi, vaqt: hozir };
    return yangi;
  } catch {
    // Tarmoq uzilsa eski keshdagi narx qoladi — u yo'q narsadan yaxshi,
    // lekin sahifa baribir ochiladi.
    return kesh.narxlar;
  }
}
