/** Bozor holati — SOF hisob-kitob, tarmoqsiz va fayl tizimisiz.
 *
 * NEGA `bozor-server.ts` DAN AJRATILGAN: bu yerdagi funksiyalar
 * brauzerda ham kerak (jadvalni saralash, foizni bo'yash), server
 * moduli esa `node:fs` ni tortadi. `jonli.ts` / `jonli-server.ts`
 * juftligida ham chegara aynan shu joydan o'tadi.
 */

/** Bitta coinning bozor holati. */
export type CoinHolati = {
  ticker: string;
  nom: string;
  logo: string | null;
  narx: number | null;
  ozgarish24: number | null;
  ozgarish7k: number | null;
  kapital: number | null;
  hajm24: number | null;
  /** 7 kunlik narx nuqtalari — mini grafik uchun. */
  chiziq: number[];
};

/** Bitta sektor (CoinGecko toifasi). */
export type SektorHolati = {
  id: string;
  nom: string;
  kapital: number | null;
  ozgarish24: number | null;
  /** Shu sektorda BIZNING ro'yxatimizdan nechta coin bor. */
  halolSoni: number;
};

/** Jadvalni nima bo'yicha saralash mumkin. */
export type SaralashKaliti =
  | "kapital"
  | "narx"
  | "ozgarish24"
  | "ozgarish7k"
  | "hajm24";

/** Saralaydi. `null` qiymatlar HAR DOIM oxirida qoladi.
 *
 * Nima uchun shunday: `null` — "ma'lumot olinmadi", nol emas. Uni
 * nol deb saralasak, narxi olinmagan coin "eng arzon" bo'lib
 * ro'yxat boshiga chiqib qolardi va bu xato ma'lumot bo'lardi.
 */
export function sarala(
  coinlar: CoinHolati[],
  kalit: SaralashKaliti,
  osib = false,
): CoinHolati[] {
  return [...coinlar].sort((a, b) => {
    const x = a[kalit];
    const y = b[kalit];
    if (x === null && y === null) return 0;
    if (x === null) return 1;
    if (y === null) return -1;
    return osib ? x - y : y - x;
  });
}

/** Foizga qarab dizayn tizimidagi rang roli.
 *
 * Nol atrofidagi kichik tebranish "o'sish" ham, "tushish" ham emas —
 * shovqin. Uni yashil qilib ko'rsatish foydalanuvchini adashtiradi.
 */
export function foizRangi(
  foiz: number | null,
): "yaxshi" | "past" | "neytral" {
  if (foiz === null) return "neytral";
  if (foiz > 0.1) return "yaxshi";
  if (foiz < -0.1) return "past";
  return "neytral";
}

/** Issiqlik xaritasidagi to'rtburchak o'lchami — kapital ulushi.
 *
 * Kvadrat ildiz olinadi: kapital farqi juda katta (BTC boshqalardan
 * yuzlab marta yirik) va to'g'ridan-to'g'ri ulushda BTC butun
 * ekranni egallab, qolgani ko'rinmas nuqtaga aylanardi.
 */
export function xaritaUlushi(kapital: number | null, jami: number): number {
  if (kapital === null || kapital <= 0 || jami <= 0) return 0;
  return Math.sqrt(kapital / jami);
}

/** Katta sonni qisqartiradi: 1 234 567 890 -> "1.23B".
 *
 * `null` uchun chiziqcha qaytadi — "0" emas. Bu butun loyihadagi
 * qoida: ma'lumot yo'qligi nol deb ko'rsatilmaydi.
 */
export function qisqaSon(qiymat: number | null): string {
  if (qiymat === null) return "—";
  const belgi = qiymat < 0 ? "-" : "";
  const son = Math.abs(qiymat);
  if (son >= 1e12) return `${belgi}${(son / 1e12).toFixed(2)}T`;
  if (son >= 1e9) return `${belgi}${(son / 1e9).toFixed(2)}B`;
  if (son >= 1e6) return `${belgi}${(son / 1e6).toFixed(2)}M`;
  if (son >= 1e3) return `${belgi}${(son / 1e3).toFixed(2)}K`;
  return `${belgi}${son.toFixed(2)}`;
}

/** Narxni ko'rsatish: arzon coinda ko'proq raqam kerak.
 *
 * $0.00 deb ko'rsatilgan narx — ma'lumot emas, xato. SHIB kabi
 * coinlarda narx 0.00001 atrofida bo'ladi.
 */
export function narxMatn(narx: number | null): string {
  if (narx === null) return "—";
  if (narx >= 1000) return `$${narx.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  if (narx >= 1) return `$${narx.toFixed(2)}`;
  if (narx >= 0.01) return `$${narx.toFixed(4)}`;
  return `$${narx.toFixed(8)}`;
}

/** Mini grafik uchun SVG `points` qatori.
 *
 * Bo'sh yoki bitta nuqtali qatordan grafik chiqmaydi — `null`
 * qaytadi va chaqiruvchi grafik o'rniga hech narsa ko'rsatmaydi.
 */
export function chiziqNuqtalari(
  qiymatlar: number[],
  eni: number,
  boyi: number,
): string | null {
  if (qiymatlar.length < 2) return null;
  const eng_past = Math.min(...qiymatlar);
  const eng_yuqori = Math.max(...qiymatlar);
  const oraliq = eng_yuqori - eng_past;

  return qiymatlar
    .map((q, i) => {
      const x = (i / (qiymatlar.length - 1)) * eni;
      // Tekis chiziq (oraliq nol) o'rtadan o'tsin, tepadan emas.
      const nisbat = oraliq === 0 ? 0.5 : (q - eng_past) / oraliq;
      const y = boyi - nisbat * boyi;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}
