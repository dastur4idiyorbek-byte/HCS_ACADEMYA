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

/** Treemap katakchasi — foizda (0-100), CSS uchun tayyor. */
export type Katak = {
  kalit: string;
  x: number;
  y: number;
  en: number;
  boy: number;
};

/** Issiqlik xaritasi joylashuvi — qatorlab treemap.
 *
 * NEGA ODDIY QATOR EMAS. Kripto saytlaridagi issiqlik xaritasi
 * to'rtburchaklarni MAYDONI bo'yicha joylashtiradi: BTC katta
 * to'rtburchak, kichik coin kichik. Bir qatorga terib chiqilsa
 * (`flex-wrap`) maydon emas, faqat kenglik farq qiladi va xarita
 * "bir qarashda manzara" xususiyatini yo'qotadi.
 *
 * USUL. Elementlar kattaligi bo'yicha tartiblanadi va qatorlarga
 * bo'linadi. Qator "to'ldi" deb hisoblanadi, qachonki keyingi
 * elementni qo'shish o'sha qatordagi to'rtburchaklarning shaklini
 * yomonlashtirsa (juda cho'zilib ketsa). Bu — `squarify`
 * algoritmining soddalashtirilgan, lekin xuddi shu g'oyadagi
 * varianti: maqsad har bir to'rtburchakni kvadratga yaqin ushlash.
 *
 * Qaytadigan qiymat FOIZDA: chaqiruvchi uni to'g'ridan-to'g'ri
 * `style` ga qo'yadi va o'lchamni o'zi hisoblamaydi.
 */
export function treemap(
  elementlar: { kalit: string; ogirlik: number }[],
  nisbat = 1.6,
): Katak[] {
  const musbat = elementlar
    .filter((e) => e.ogirlik > 0)
    .sort((a, b) => b.ogirlik - a.ogirlik);
  if (musbat.length === 0) return [];

  const kataklar: Katak[] = [];

  let y = 0;
  let i = 0;

  while (i < musbat.length) {
    // Qolgan balandlik bo'yicha qator to'planadi.
    const qoldiq = musbat.slice(i).reduce((s, e) => s + e.ogirlik, 0);
    const qolganBoy = 100 - y;

    const qator: typeof musbat = [];
    let qatorOgirlik = 0;
    let engYaxshi = Number.POSITIVE_INFINITY;

    for (let j = i; j < musbat.length; j++) {
      const yangiOgirlik = qatorOgirlik + musbat[j].ogirlik;
      const boy = (yangiOgirlik / qoldiq) * qolganBoy;
      // Qator ichidagi ENG YOMON shakl: eng kichik element qanchalik
      // cho'zilgan. Shu ko'rsatkich yomonlashsa, qator to'lgan.
      const engKichik = musbat[j].ogirlik;
      const en = (engKichik / yangiOgirlik) * 100;
      const yomonlik = Math.max(en / boy, boy / en);

      if (qator.length > 0 && yomonlik > engYaxshi * nisbat) break;

      qator.push(musbat[j]);
      qatorOgirlik = yangiOgirlik;
      engYaxshi = Math.min(engYaxshi, yomonlik);
    }

    const boy = (qatorOgirlik / qoldiq) * qolganBoy;
    let x = 0;
    for (const element of qator) {
      const en = (element.ogirlik / qatorOgirlik) * 100;
      kataklar.push({ kalit: element.kalit, x, y, en, boy });
      x += en;
    }

    y += boy;
    i += qator.length;
    // Qavariq holatlarda (juda kichik qoldiq) tsikl to'xtamay
    // qolmasin: bitta element ham olinmasa, majburan olinadi.
    if (qator.length === 0) i++;
  }

  return kataklar;
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

/** To'ldirilgan mini grafik uchun yopiq SVG yo'li.
 *
 * NEGA TO'LDIRILGAN. Kripto saytlarida mini grafik ingichka chiziq
 * emas, ostidan bo'yalgan maydon bo'ladi — kichik o'lchamda chiziq
 * ko'zga ilinmaydi, maydon esa yo'nalishni darrov ko'rsatadi.
 */
export function chiziqMaydoni(
  qiymatlar: number[],
  eni: number,
  boyi: number,
): string | null {
  const nuqtalar = chiziqNuqtalari(qiymatlar, eni, boyi);
  if (nuqtalar === null) return null;
  return `M0,${boyi} L${nuqtalar.split(" ").join(" L")} L${eni},${boyi} Z`;
}

/** "Altcoin mavsumi" ko'rsatkichi — 0 dan 100 gacha.
 *
 * NEGA O'ZIMIZ HISOBLAYMIZ. Tayyor manba (blockchaincenter) ochiq
 * API bermaydi. Lekin ko'rsatkichning o'zi sodda: 7 kun ichida
 * altcoinlarning necha foizi BITCOINDAN yaxshiroq yurgan.
 *
 * MUHIM CHEKLOV — SAHIFADA YOZILISHI SHART: bu bizning 80 talik
 * HALOL ro'yxatimiz bo'yicha hisoblanadi, butun bozor bo'yicha emas.
 * Shuning uchun u boshqa saytlardagi raqamdan farq qiladi. Bu xato
 * emas, boshqa savolga javob: "halol doiradagi altcoinlar BTC dan
 * yaxshiroqmi?".
 *
 * BTC ning o'zi hisobga kirmaydi — u o'lchov, ishtirokchi emas.
 * Ma'lumot yetarli bo'lmasa `null`: taxminiy raqam ko'rsatishdan
 * ko'ra bo'shliq halolroq.
 */
export function altcoinMavsumi(coinlar: CoinHolati[]): number | null {
  const btc = coinlar.find((c) => c.ticker === "BTC");
  if (btc === undefined || btc.ozgarish7k === null) return null;

  const altlar = coinlar.filter(
    (c) => c.ticker !== "BTC" && c.ozgarish7k !== null,
  );
  if (altlar.length < 10) return null;

  const yutgan = altlar.filter(
    (c) => (c.ozgarish7k as number) > (btc.ozgarish7k as number),
  ).length;
  return Math.round((yutgan / altlar.length) * 100);
}
