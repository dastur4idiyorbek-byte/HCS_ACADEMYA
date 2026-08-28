/** Trading kalkulyatori — SOF hisob-kitob.
 *
 * Alohida modul, chunki bu yagona joy bo'lishi kerak: raqamlar
 * komponent ichida hisoblansa, ularni test qilib bo'lmasdi va bitta
 * noto'g'ri formula ekranga chiqib ketardi.
 *
 * MUHIM: bu — faqat hisob-kitob vositasi, moliyaviy maslahat emas.
 */

export type TpKirish = {
  /** TP narxi */
  narx: number;
  /** Shu TP da pozitsiyaning necha foizi sotiladi */
  ulush: number;
};

export type TpNatija = {
  ulush: number;
  narx: number;
  /** Shu TP da sotiladigan miqdor (asosiy aktivda, masalan BTC) */
  miqdor: number;
  /** Sotuvdan tushadigan summa */
  tushum: number;
  /** Foyda (tushum minus shu miqdorning kirish qiymati) */
  foyda: number;
  /** Narx o'zgarishi foizi — ULUSHGA bog'liq emas */
  foizOzgarish: number;
};

export type Hisob = {
  /** Sarflangan summaga sotib olinadigan umumiy miqdor */
  umumiyMiqdor: number;
  tplar: TpNatija[];
  /** Barcha miqdor Stop'da yopilsa */
  stopZarar: number;
  stopFoiz: number;
  /** Barcha TP ketma-ket urilsa */
  jamiFoyda: number;
  jamiFoiz: number;
  /** Ulushlar yig'indisi — 100 bo'lishi kerak */
  ulushJami: number;
  toliqmi: boolean;
};

export const ULUSH_JAMI = 100;

/** Kiritilgan qiymat son ekanini tekshiradi.
 *
 * Bo'sh maydon `Number("")` da 0 beradi — bu esa hisobni jimgina nolga
 * aylantirardi. Shuning uchun nol ham "yaroqsiz" deb qaraladi.
 */
export function musbatSon(x: unknown): number | null {
  const n = typeof x === "number" ? x : Number(String(x ?? "").replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function hisobla(
  summa: number,
  entry: number,
  stop: number,
  tplar: TpKirish[],
): Hisob | null {
  if (!(summa > 0) || !(entry > 0)) return null;

  const umumiyMiqdor = summa / entry;
  const ulushJami = tplar.reduce((s, t) => s + (Number.isFinite(t.ulush) ? t.ulush : 0), 0);

  const natijalar: TpNatija[] = tplar.map((t) => {
    const ulush = Number.isFinite(t.ulush) ? t.ulush : 0;
    const miqdor = umumiyMiqdor * (ulush / 100);
    const tushum = miqdor * t.narx;
    return {
      ulush,
      narx: t.narx,
      miqdor,
      tushum,
      foyda: tushum - miqdor * entry,
      // Foiz ULUSHGA bog'liq emas: u shu narxgacha bo'lgan harakat.
      foizOzgarish: ((t.narx - entry) / entry) * 100,
    };
  });

  const jamiFoyda = natijalar.reduce((s, t) => s + t.foyda, 0);

  return {
    umumiyMiqdor,
    tplar: natijalar,
    // Stop butun pozitsiyaga qo'llanadi — TP ulushlaridan qat'i nazar.
    stopZarar: stop > 0 ? umumiyMiqdor * (entry - stop) : 0,
    stopFoiz: stop > 0 ? ((stop - entry) / entry) * 100 : 0,
    jamiFoyda,
    jamiFoiz: (jamiFoyda / summa) * 100,
    ulushJami,
    toliqmi: Math.abs(ulushJami - ULUSH_JAMI) < 0.01,
  };
}

/** Ulushlarni teng bo'lib beradi. Qoldiq oxirgisiga qo'shiladi —
 *  3 ta TP da 33.33+33.33+33.33 = 99.99 bo'lib qolmasin. */
export function tengUlushlar(soni: number): number[] {
  if (soni <= 0) return [];
  const asos = Math.floor((ULUSH_JAMI / soni) * 100) / 100;
  const ulushlar = Array.from({ length: soni }, () => asos);
  ulushlar[soni - 1] = Math.round((ULUSH_JAMI - asos * (soni - 1)) * 100) / 100;
  return ulushlar;
}

/** Bitta TP ulushi o'zgarganda QOLGANLARINI qayta taqsimlaydi.
 *
 * NEGA KERAK: ikkita TP bo'lsa va foydalanuvchi TP1 ga 75% yozsa, TP2
 * o'z-o'zidan 25% bo'lishi kerak — chunki pozitsiya bitta va u to'liq
 * sotiladi. Avval ikkala maydon mustaqil edi: 75 va 50 yozilib qolsa
 * kalkulyator 125% pozitsiyani hisoblab, mavjud bo'lmagan foydani
 * ko'rsatardi.
 *
 * IKKITADAN KO'P TP uchun qoida: qolgan ulush boshqalarga ULARNING
 * NISBATIDA taqsimlanadi. Ya'ni 50/30/20 da TP1 ni 60 qilsak, TP2 va
 * TP3 o'z nisbatini saqlagan holda 24/16 bo'ladi — foydalanuvchi
 * qo'lda sozlagan muvozanat buzilmaydi.
 *
 * Yaxlitlash qoldig'i OXIRGI tahrirlanmagan ulushga beriladi, shunda
 * yig'indi HAR DOIM aniq 100 bo'ladi.
 */
export function ulushlarniTengla(
  ulushlar: number[],
  indeks: number,
  yangi: number,
): number[] {
  const n = ulushlar.length;
  if (n === 0) return [];
  if (n === 1) return [ULUSH_JAMI];

  // Chegaradan chiqqan qiymat kesiladi: 150% yozilsa boshqalari manfiy
  // bo'lib qolardi va hisob ma'nosini yo'qotardi.
  const qiymat = Math.min(Math.max(Number.isFinite(yangi) ? yangi : 0, 0), ULUSH_JAMI);
  const qolgan = ULUSH_JAMI - qiymat;

  const musbat = (x: number) => (Number.isFinite(x) && x > 0 ? x : 0);
  const boshqaJami = ulushlar.reduce(
    (s, x, i) => (i === indeks ? s : s + musbat(x)),
    0,
  );

  const natija = ulushlar.map((eski, i) => {
    if (i === indeks) return qiymat;
    // Boshqalari hammasi nol bo'lsa nisbat yo'q — teng bo'linadi.
    const ulush =
      boshqaJami > 0 ? (qolgan * musbat(eski)) / boshqaJami : qolgan / (n - 1);
    return Math.round(ulush * 100) / 100;
  });

  // Yaxlitlashdan keyin yig'indi 99.99 yoki 100.003 bo'lib qolishi
  // mumkin (tahrirlangan qiymatning o'zi ham kasrli bo'lishi mumkin —
  // masalan 33.333). Oxirgi tahrirlanmagan ulush QOLDIQDAN hisoblanadi,
  // qayta yaxlitlanmaydi: aks holda tuzatish yana yo'qolardi.
  const oxirgi = indeks === n - 1 ? n - 2 : n - 1;
  const boshqalarJami = natija.reduce((s, x, i) => (i === oxirgi ? s : s + x), 0);
  // 1e-9 gacha yaxlitlash — bu suzuvchi nuqta shovqinini oladi, lekin
  // haqiqiy qoldiqni saqlaydi.
  natija[oxirgi] = Math.round((ULUSH_JAMI - boshqalarJami) * 1e9) / 1e9;
  return natija;
}

/** `BTCUSDT` -> `BTC`. Miqdorni qaysi aktivda ko'rsatishni bilish uchun. */
export function asosiyAktiv(symbol: string, quote = "USDT"): string {
  const s = symbol.toUpperCase();
  const q = quote.toUpperCase();
  return s.endsWith(q) && s.length > q.length ? s.slice(0, -q.length) : s;
}

/** Birja juftligi nomi — grafik uchun: `DOT` -> `DOTUSDT`.
 *
 * NEGA KERAK BO'LDI: loyihada `symbol` — bu ASOSIY AKTIV (`DOT`,
 * `BTC`), birja juftligi emas. Bot uni `quote_asset` bilan qo'shib
 * yasaydi (`core/halal_screening/screener.py` -> `pair_for()`).
 * Grafikka `BINANCE:DOT` berilgan edi va TradingView "This symbol
 * doesn't exist" deb turdi.
 *
 * Xato SINOV MA'LUMOTI tufayli ko'rinmadi: mahalliy bazada coinlar
 * `BTCUSDT` deb yozilgan edi, ya'ni sinovda tasodifan to'g'ri
 * chiqardi. Shuning uchun bu funksiya IKKALA shaklni ham qabul
 * qiladi — juftlik allaqachon berilgan bo'lsa, ikkinchi marta
 * qo'shilmaydi.
 */
export function birjaJuftligi(symbol: string, quote = "USDT"): string {
  const q = quote.toUpperCase();
  return `${asosiyAktiv(symbol, q)}${q}`;
}

/** Narxni kiritish maydoni uchun matn.
 *
 * Kasr xonalari narxning KATTALIGIGA qarab tanlanadi: `0.869` uchun
 * ikkita xona yetmaydi, `61250.5` uchun sakkiztasi ortiqcha.
 *
 * Guruh ajratgichi (`1,150.74`) ATAYLAB QO'YILMAYDI: maydon
 * tahrirlanadi va vergul `musbatSon()` da kasr belgisi deb
 * o'qilardi — `1,150.74` "1.150.74" ga aylanib, butun hisob buzilardi.
 */
export function narxMatni(n: number): string {
  const xona = n >= 1000 ? 2 : n >= 1 ? 4 : n >= 0.01 ? 6 : 8;
  return n.toFixed(xona).replace(/\.?0+$/, "");
}
