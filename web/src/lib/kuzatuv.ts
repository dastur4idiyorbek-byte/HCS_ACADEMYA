/** Kuzatuv paneli — tiplar va ko'rinish qoidalari (9-prompt).
 *
 * QAT'IY BIR TOMONLAMA OQIM:
 *
 *     skaner -> `kuzatuv_holatlari` -> ekran
 *
 * Bu fayl faqat XOM HOLATNI ko'rinishga aylantiradi. Hisob
 * Pythonda, `core/analysis/observation_mode.py` da qoladi va shu
 * yerdagi hech narsa unga qaytib kirmaydi.
 *
 * QAT'IY CHEGARA (9-prompt, 6-qism): bu faylda Entry, Stop yoki TP
 * tushunchasi YO'Q va bo'lmaydi ham. Zona narxlari faqat
 * KO'RSATISH uchun — ular kirish narxi EMAS.
 */

/** Coinning struktura yo'nalishi — Python `Yonalish` bilan bir xil. */
export type Yonalish = "uptrend" | "yangi_burilish" | "downtrend" | "aniq_emas";

/** Ichki tekshiruvning uch holati — Python `Holat` bilan bir xil.
 *
 * `malumot_yoq` ✅ HAM emas, ❌ HAM emas: u xira segment bo'lib
 * ko'rinadi. Uni "yo'q" deb chizish yolg'on bo'lardi — biz
 * o'lchamadik, salbiy javob olmadik. */
export type SegmentHolati = "ha" | "yoq" | "malumot_yoq";

export type ZonaDarajasi = "yoq" | "zaif" | "orta" | "kuchli";

/** Coin qaysi ro'yxatda. */
export type RoyxatTuri = "top" | "kuzatuvda" | "royxatdan_tashqari";

export type Segment = {
  nom: string;
  holat: SegmentHolati;
  izoh: string;
  /** Qaysi grafikdan o'qildi — ekranda aynan shu yoziladi */
  timeframe: string;
};

export type BlokTekshiruvi = {
  nom: string;
  holat: SegmentHolati;
  izoh: string;
};

export type KuzatuvBlok = {
  nom: string;
  kuch: number;
  maxraj: number;
  otdi: boolean;
  olchanmadi: boolean;
  tosiq: string | null;
  tekshiruvlar: BlokTekshiruvi[];
};

export type KuzatuvCoin = {
  symbol: string;
  yonalish: Yonalish;
  yonalishIzoh: string;
  otdi: boolean;
  diqqat: number;
  segmentlar: Segment[];
  bloklar: KuzatuvBlok[];
  zonaDarajasi: ZonaDarajasi;
  zonaPast: number | null;
  zonaYuqori: number | null;
  /** Delisting/unlock xavfi — coinni ro'yxatdan CHIQARMAYDI */
  ogohlantirish: string | null;
  nisbiyKuch: number | null;
  royxat: RoyxatTuri;
  orin: number | null;
  tekshirilgan: string | null;
};

export type SkanHolati = {
  holat: "bosh" | "yurmoqda" | "tugadi" | "xato";
  sorov: boolean;
  tekshirildi: number;
  otdi: number;
  izoh: string;
  boshlandi: string | null;
  tugadi: string | null;
};

/** Nechta segment bo'ladi — indikator shuncha katakcha chizadi.
 *
 * Pythondagi `observation_mode.kuzatuv_yur` aynan shuncha segment
 * qaytaradi. Ikkalasi ajralib ketmasligini `web/tests/kuzatuv.test.ts`
 * tekshiradi. */
export const SEGMENT_SONI = 4;

/** Segment kalitining ekrandagi nomi — i18n kaliti.
 *
 * Python nomlari (`zona_konfluensiya`) to'g'ridan-to'g'ri
 * ko'rsatilmaydi: ular kod nomi, foydalanuvchi tili emas. */
export const SEGMENT_KALITI: Record<string, string> = {
  zona_konfluensiya: "kuzatuv.segment.zona",
  volume_profile: "kuzatuv.segment.hajm",
  liquidity_sweep: "kuzatuv.segment.sweep",
  rsi_divergensiya: "kuzatuv.segment.rsi",
};

/** Blok nomining i18n kaliti. */
export const BLOK_KALITI: Record<string, string> = {
  Fundamental: "kuzatuv.blok.fundamental",
  Struktura: "kuzatuv.blok.struktura",
  "Zona Sifati": "kuzatuv.blok.zona",
  Tasdiqlash: "kuzatuv.blok.tasdiqlash",
};

/** Zona narx oralig'ining hozirgi narxga nisbatan joyi.
 *
 * SMC atamasi: narx oxirgi impuls oralig'ining pastki yarmida
 * bo'lsa — "discount" (arzon), yuqori yarmida — "premium".
 *
 * BU QAROR EMAS. Faqat rang: 🟢 / 🟡 / 🔴. Hech qanday kirish
 * tavsiyasi bermaydi. */
export type ZonaJoyi = "discount" | "ortada" | "premium" | "nomalum";

export function zonaJoyi(
  narx: number | null,
  past: number | null,
  yuqori: number | null,
): ZonaJoyi {
  if (narx === null || past === null || yuqori === null) return "nomalum";
  if (!Number.isFinite(narx) || yuqori <= past) return "nomalum";
  const ulush = (narx - past) / (yuqori - past);
  if (ulush < 0.4) return "discount";
  if (ulush > 0.6) return "premium";
  return "ortada";
}

/** Yo'nalish ikonkasi — matn emas, VIZUAL (5.2-qism). */
export function yonalishBelgisi(y: Yonalish): "trend" | "yangilash" | "pastga" | "malumot" {
  if (y === "uptrend") return "trend";
  if (y === "yangi_burilish") return "yangilash";
  if (y === "downtrend") return "pastga";
  return "malumot";
}

/** Blok ramkasining rangi (5.3-qism): HA — yashil, YO'Q — kulrang.
 *
 * O'lchanmagan blok UCHINCHI holat: u "yo'q" emas. Kulrang, lekin
 * izohi boshqacha — "manba ulanmagan". */
export function blokRangi(b: KuzatuvBlok): "yaxshi" | "past" | "sokin" {
  if (b.olchanmadi) return "sokin";
  return b.otdi ? "yaxshi" : "past";
}
