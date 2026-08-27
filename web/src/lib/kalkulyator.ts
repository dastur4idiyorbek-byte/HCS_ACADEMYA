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

/** `BTCUSDT` -> `BTC`. Miqdorni qaysi aktivda ko'rsatishni bilish uchun. */
export function asosiyAktiv(symbol: string, quote = "USDT"): string {
  const s = symbol.toUpperCase();
  const q = quote.toUpperCase();
  return s.endsWith(q) && s.length > q.length ? s.slice(0, -q.length) : s;
}
