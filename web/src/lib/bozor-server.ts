import { COINGECKO_ID } from "./coingecko-id.ts";
import { sozlama } from "./config.ts";
import type { CoinHolati, SektorHolati } from "./bozor.ts";

/** Bozor holati ma'lumotini CoinGecko'dan olish — faqat SERVER.
 *
 * NEGA COINGECKO: loyihada allaqachon ishlatiladi
 * (`core/market_data/global_metrics.py`), kalit talab qilmaydi va
 * bitta so'rovda narx + kapital + hajm + 24s% + 7k% + mini grafik
 * beradi. CoinMarketCap kaliti bu sahifa uchun kerak emas.
 *
 * NEGA SERVERDA: kesh shu yerda tursin. Yuzta obunachi sahifani
 * ochsa CoinGecko'ga yuzta emas, o'n besh daqiqada bir so'rov ketadi.
 * CoinGecko'ning bepul chegarasi qattiq va undan oshsak sahifa
 * HAMMA uchun bo'shab qoladi.
 *
 * HECH QACHON ISTISNO TASHLAMAYDI: bozor holati — qo'shimcha
 * ma'lumot. CoinGecko javob bermasa sahifa bo'sh ro'yxat oladi va
 * "ma'lumot olinmadi" deb yozadi. Signal chiqishiga bu hech qanday
 * ta'sir qilmaydi — bu sahifa BIR TOMONLAMA, moduldan mustaqil.
 */

/** Kesh muddati — 15 daqiqa.
 *
 * Bu sahifa savdo qarori uchun emas, umumiy manzara uchun. Bir
 * daqiqalik aniqlik kerak emas, CoinGecko chegarasi esa haqiqiy.
 */
export const KESH_MS = 15 * 60 * 1000;

type Kesh<T> = { qiymat: T; vaqt: number };

let coinKesh: Kesh<CoinHolati[]> | null = null;
let sektorKesh: Kesh<SektorHolati[]> | null = null;

function asos(): string {
  return sozlama<string>(
    ["market_data", "coingecko_base_url"],
    "https://api.coingecko.com/api/v3",
  );
}

async function soragich(manzil: string): Promise<unknown | null> {
  try {
    const javob = await fetch(manzil, {
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(12_000),
    });
    if (!javob.ok) return null;
    return await javob.json();
  } catch {
    return null;
  }
}

function son(qiymat: unknown): number | null {
  return typeof qiymat === "number" && Number.isFinite(qiymat) ? qiymat : null;
}

/** 80 talik ro'yxatning bozor holati.
 *
 * `tickerlar` — `TERMINAL_COINLARI` emas, chaqiruvchi beradigan
 * ro'yxat: sahifa `core/config/schema.py` dagi 80 talikni uzatadi.
 */
export async function coinHolatlari(
  tickerlar: string[],
): Promise<CoinHolati[]> {
  const hozir = Date.now();
  if (coinKesh && hozir - coinKesh.vaqt < KESH_MS) return coinKesh.qiymat;

  // Faqat jadvalda `id` si bor tickerlar so'raladi. Jadvalda yo'q
  // ticker jimgina tushib qolmasin — u ham natijada "ma'lumot yo'q"
  // bo'lib turishi kerak, shuning uchun quyida qayta qo'shiladi.
  const idlar = tickerlar
    .map((t) => COINGECKO_ID[t])
    .filter((id): id is string => Boolean(id));
  if (idlar.length === 0) return [];

  const manzil =
    `${asos()}/coins/markets?vs_currency=usd` +
    `&ids=${idlar.join(",")}` +
    `&price_change_percentage=24h,7d` +
    `&sparkline=true&per_page=250&page=1`;

  const javob = await soragich(manzil);
  if (!Array.isArray(javob)) {
    // Eski kesh yangisidan yaxshiroq: 20 daqiqalik narx "—" dan
    // foydaliroq. Lekin kesh butunlay yo'q bo'lsa bo'sh qaytadi.
    return coinKesh?.qiymat ?? [];
  }

  const idBoyicha = new Map<string, string>();
  for (const [ticker, id] of Object.entries(COINGECKO_ID)) {
    idBoyicha.set(id, ticker);
  }

  const olingan = new Map<string, CoinHolati>();
  for (const qator of javob) {
    if (typeof qator !== "object" || qator === null) continue;
    const q = qator as Record<string, unknown>;
    const id = typeof q.id === "string" ? q.id : null;
    if (id === null) continue;

    const kutilgan = idBoyicha.get(id);
    if (kutilgan === undefined) continue;

    // ENG MUHIM TEKSHIRUV. `coingecko-id.ts` jadvali qo'lda yozilgan
    // va bittalab tekshirilmagan. Agar `id` xato bo'lsa, CoinGecko
    // BOSHQA coinning ma'lumotini qaytaradi — narx bor, grafik bor,
    // hammasi to'g'ridek ko'rinadi. Javobdagi `symbol` biz kutgan
    // ticker bilan solishtiriladi va mos kelmasa qator TASHLANADI:
    // jimgina noto'g'ri raqam ko'rsatishdan ko'ra ochiq bo'shliq
    // xavfsizroq.
    const belgi =
      typeof q.symbol === "string" ? q.symbol.toUpperCase() : null;
    if (belgi !== kutilgan) continue;

    const chiziq = (
      q.sparkline_in_7d as { price?: unknown } | undefined
    )?.price;

    olingan.set(kutilgan, {
      ticker: kutilgan,
      nom: typeof q.name === "string" ? q.name : kutilgan,
      logo: typeof q.image === "string" ? q.image : null,
      narx: son(q.current_price),
      ozgarish24: son(q.price_change_percentage_24h_in_currency),
      ozgarish7k: son(q.price_change_percentage_7d_in_currency),
      kapital: son(q.market_cap),
      hajm24: son(q.total_volume),
      chiziq: Array.isArray(chiziq)
        ? chiziq.filter((x): x is number => typeof x === "number")
        : [],
    });
  }

  // Javobda kelmagan yoki tekshiruvdan o'tmagan coin ham ro'yxatda
  // TURADI — qiymatlari `null` bilan. Sahifada u "ma'lumot olinmadi"
  // bo'lib ko'rinadi. Jimgina yo'qolib qolsa, foydalanuvchi coin
  // ro'yxatdan chiqarilgan deb o'ylardi.
  const natija = tickerlar.map(
    (t) =>
      olingan.get(t) ?? {
        ticker: t,
        nom: t,
        logo: null,
        narx: null,
        ozgarish24: null,
        ozgarish7k: null,
        kapital: null,
        hajm24: null,
        chiziq: [],
      },
  );

  coinKesh = { qiymat: natija, vaqt: hozir };
  return natija;
}

/** Sektorlar (CoinGecko toifalari).
 *
 * DIQQAT — sahifada OCHIQ YOZILISHI SHART: bu foizlar BUTUN
 * BOZORDAN hisoblanadi, ya'ni ichida haram va shubhali loyihalar
 * ham bor. Bizning ro'yxatimiz esa faqat halol coinlardan iborat.
 * Ikkisi bir xil emas va foydalanuvchi buni bilishi kerak.
 *
 * Loyiha egasining qarori shu edi: tanish raqamni ko'rsatamiz,
 * lekin nimadan hisoblangani yashirilmaydi.
 */
export async function sektorHolatlari(
  halolTickerlar: string[],
): Promise<SektorHolati[]> {
  const hozir = Date.now();
  if (sektorKesh && hozir - sektorKesh.vaqt < KESH_MS) {
    return sektorKesh.qiymat;
  }

  const javob = await soragich(`${asos()}/coins/categories`);
  if (!Array.isArray(javob)) return sektorKesh?.qiymat ?? [];

  const halol = new Set(halolTickerlar);
  const natija: SektorHolati[] = [];

  for (const qator of javob) {
    if (typeof qator !== "object" || qator === null) continue;
    const q = qator as Record<string, unknown>;
    if (typeof q.id !== "string" || typeof q.name !== "string") continue;

    // `top_3_coins` faqat uchta coin beradi, shuning uchun "shu
    // sektorda bizning nechta coinimiz bor" degan son TAXMINIY.
    // Aniq son har bir sektor uchun alohida so'rov talab qiladi va
    // bu CoinGecko chegarasini yeb qo'yardi. Taxminiyligi sahifada
    // ham ko'rinadi: bu son saralash uchun emas, yo'naltirish uchun.
    const uchtasi = Array.isArray(q.top_3_coins_id) ? q.top_3_coins_id : [];
    const halolSoni = uchtasi.filter(
      (x) => typeof x === "string" && halol.has(x.toUpperCase()),
    ).length;

    natija.push({
      id: q.id,
      nom: q.name,
      kapital: son(q.market_cap),
      ozgarish24: son(q.market_cap_change_24h),
      halolSoni,
    });
  }

  sektorKesh = { qiymat: natija, vaqt: hozir };
  return natija;
}

/** Testlar uchun: keshni tozalaydi. */
export function keshniTozala(): void {
  coinKesh = null;
  sektorKesh = null;
}
