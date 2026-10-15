/** Modul 4.0.0 — "Portlash xavfi radari": tiplar va SOF yordamchilar.
 *
 * Yagona manba — `docs/MODUL_4_0_0.md`. Bu fayl uning sayt tomonidagi
 * aksi: jadval vaqti, grafik va jadval shakli, calibration hisobi.
 *
 * NEGA SOF. Bu yerda baza ham, `node:` moduli ham, `config.ts` ham
 * YO'Q. Sabablari ikkita:
 *   1. Testlar uni bazasiz, to'g'ridan-to'g'ri chaqiradi — "kun
 *      chegarasi 23:45 UTC da to'g'ri o'tadimi" degan savolga javob
 *      bazaga bog'liq bo'lmasligi kerak.
 *   2. Mijoz komponenti ham uni import qila oladi. `node:fs` mijoz
 *      to'plamiga tushsa `next build` yiqiladi
 *      (`tests/mijoz-serverni-tortmasin.test.ts`).
 * YAML dagi qiymatlar (jadval daqiqalari, vaqt zonasi) shuning uchun
 * PARAMETR bo'lib keladi — ularni sahifa o'qiydi.
 *
 * QAT'IY CHEGARA: modul SIGNAL BERMAYDI. Bu faylda kirish, stop yoki
 * nishon narxi hisoblanmaydi va hisoblanmaydi ham — faqat "nima
 * bo'ldi" va "keyin nima bo'ldi" (calibration).
 */

// --------------------------------------------------------------------------- //
//  Sozlamalar (13- va 15-bo'lim)
// --------------------------------------------------------------------------- //

export type SozlamaKalit =
  | "min_kapitalizatsiya_usd"
  | "min_hajm_24s_usd"
  | "elak_hajm_x"
  | "yangi_listing_kun"
  | "hajm_x"
  | "narx_ozgarish_pct"
  | "funding_8s_pct"
  | "oi_osish_pct"
  | "long_short_nisbat"
  | "btc_farq_pp"
  | "aylanma_max_pct"
  | "unlock_kun"
  | "unlock_min_pct"
  | "nomzod_min"
  | "top_n"
  | "namuna_soni"
  | "portlash_24s_pct"
  | "portlash_7k_pct";

/** Ruxsat etilgan oraliq — 15-bo'limdagi jadval.
 *
 * DIQQAT — SHAKLI QAT'IY: Python testi bu blokni MATN sifatida o'qib,
 * botdagi oraliqlar bilan solishtiradi. Har kalit alohida qatorda,
 * raqamlar oddiy JS yozuvida qolsin — aks holda ikki tomon jimgina
 * ajralib ketadi va sayt bot rad etadigan qiymatni saqlab qo'yadi.
 */
export const SOZLAMA_ORALIQLARI: Record<SozlamaKalit, readonly [number, number]> = {
  min_kapitalizatsiya_usd: [0, 1e11],
  min_hajm_24s_usd: [0, 1e11],
  elak_hajm_x: [1, 100],
  yangi_listing_kun: [0, 365],
  hajm_x: [1, 100],
  narx_ozgarish_pct: [1, 1000],
  funding_8s_pct: [0.001, 10],
  oi_osish_pct: [1, 1000],
  long_short_nisbat: [1, 100],
  btc_farq_pp: [1, 1000],
  aylanma_max_pct: [1, 100],
  unlock_kun: [1, 180],
  unlock_min_pct: [0.01, 100],
  nomzod_min: [1, 7],
  top_n: [3, 30],
  namuna_soni: [0, 50],
  portlash_24s_pct: [1, 1000],
  portlash_7k_pct: [1, 1000],
};

/** Butun son bo'lishi shart bo'lgan kalitlar (kun, dona, o'rin). */
export const BUTUN_KALITLAR: readonly SozlamaKalit[] = ["yangi_listing_kun", "unlock_kun", "nomzod_min", "top_n", "namuna_soni"];

/** Kalitlar sahifadagi tartibda — bosqichlar ketma-ketligida. */
export const SOZLAMA_KALITLARI = Object.keys(SOZLAMA_ORALIQLARI) as SozlamaKalit[];

/** Standart qiymatlar — YAML o'qilmay qolgan holat uchun ZAXIRA.
 *
 * Asosiy manba `config/default.yaml` (`radar:`). Bu yerdagilar
 * 15-bo'limdagi jadval bilan bir xil va faqat YAML da kalit yo'q
 * bo'lsa ishlaydi.
 */
export const SOZLAMA_STANDART: Record<SozlamaKalit, number> = {
  min_kapitalizatsiya_usd: 10_000_000,
  min_hajm_24s_usd: 500_000,
  elak_hajm_x: 3,
  yangi_listing_kun: 30,
  hajm_x: 5,
  narx_ozgarish_pct: 20,
  funding_8s_pct: 0.1,
  oi_osish_pct: 30,
  long_short_nisbat: 2.5,
  btc_farq_pp: 15,
  aylanma_max_pct: 60,
  unlock_kun: 7,
  unlock_min_pct: 5,
  nomzod_min: 4,
  top_n: 10,
  namuna_soni: 10,
  portlash_24s_pct: 20,
  portlash_7k_pct: 50,
};

export function sozlamaKalitmi(x: unknown): x is SozlamaKalit {
  return typeof x === "string" && Object.hasOwn(SOZLAMA_ORALIQLARI, x);
}

export type SozlamaXatosi = "kalit" | "son" | "oraliq" | "butun";

/** Admin kiritgan qiymat to'g'rimi.
 *
 * Sayt bu tekshiruvsiz yozsa, bot keyingi sessiyada absurd chegara
 * bilan ishlardi (masalan `top_n = 0` — grafik bo'sh, yoki
 * `nomzod_min = 9` — hech kim hech qachon nomzod bo'lmaydi). Rad
 * etilgan qiymat bazaga UMUMAN tushmaydi.
 */
export function sozlamaTekshir(
  kalit: string,
  qiymat: number,
): { ok: true; kalit: SozlamaKalit; qiymat: number } | { ok: false; xato: SozlamaXatosi } {
  if (!sozlamaKalitmi(kalit)) return { ok: false, xato: "kalit" };
  if (typeof qiymat !== "number" || !Number.isFinite(qiymat)) {
    return { ok: false, xato: "son" };
  }
  const [past, yuqori] = SOZLAMA_ORALIQLARI[kalit];
  if (qiymat < past || qiymat > yuqori) return { ok: false, xato: "oraliq" };
  if (BUTUN_KALITLAR.includes(kalit) && !Number.isInteger(qiymat)) {
    return { ok: false, xato: "butun" };
  }
  return { ok: true, kalit, qiymat };
}

/** Forma matnini songa: "10 000 000", "0,1" kabi yozuvlar ham o'tadi.
 *  Bo'sh yoki son bo'lmagan matn — `NaN` (tekshiruvda rad etiladi). */
export function sonniOqi(xom: unknown): number {
  const matn = String(xom ?? "")
    .trim()
    .replace(/[\s_]/g, "")
    .replace(",", ".");
  if (matn === "") return Number.NaN;
  return Number(matn);
}

/** `sozlama_json` — sessiya ishlatgan chegaralar. Buzuq JSON yoki
 *  noma'lum kalit jimgina tashlanadi: sahifa yiqilmasin. */
export function sozlamaJsonOqi(xom: unknown): Partial<Record<SozlamaKalit, number>> {
  const natija: Partial<Record<SozlamaKalit, number>> = {};
  const obyekt = jsonObyekt(xom);
  for (const [k, v] of Object.entries(obyekt)) {
    if (sozlamaKalitmi(k) && typeof v === "number" && Number.isFinite(v)) {
      natija[k] = v;
    }
  }
  return natija;
}

// --------------------------------------------------------------------------- //
//  Coinni yashirish — symbol
// --------------------------------------------------------------------------- //

/** Admin yozgan nomni Binance Futures symboliga keltiradi.
 *
 * "lsk", "LSK", "lskusdt", "LSK/USDT" -> "LSKUSDT". Bot jadvalni
 * aynan shu ko'rinishda solishtiradi: "LSK" deb saqlansa, yashirish
 * jimgina ishlamay qolardi. Faqat `[A-Z0-9]{2,30}USDT` o'tadi — boshqa
 * har narsa (bo'sh joy, belgilar, SQL bo'lagi) `null`.
 */
export function symbolNormalla(xom: unknown): string | null {
  const toza = String(xom ?? "")
    .trim()
    .toUpperCase()
    .replace(/[\s/\-_]/g, "");
  if (!toza) return null;
  const symbol = toza.endsWith("USDT") ? toza : `${toza}USDT`;
  return /^[A-Z0-9]{2,30}USDT$/.test(symbol) ? symbol : null;
}

/** Yashirish muddati: kunlar yoki `null` (doimiy). */
export const YASHIRISH_MUDDATLARI = ["1", "7", "30", "doimiy"] as const;
export type YashirishMuddati = (typeof YASHIRISH_MUDDATLARI)[number];

export function yashirishGacha(muddat: unknown, hozir: Date): Date | null | undefined {
  // `undefined` — noto'g'ri muddat (rad etiladi), `null` — doimiy.
  if (muddat === "doimiy") return null;
  if (muddat === "1" || muddat === "7" || muddat === "30") {
    return new Date(hozir.getTime() + Number(muddat) * KUN_MS);
  }
  return undefined;
}

// --------------------------------------------------------------------------- //
//  Vaqt jadvali (8-bo'lim) — `core/portlash_radari/vaqt.py` ning aksi
// --------------------------------------------------------------------------- //

const SOAT_MS = 3_600_000;
const DAQIQA_MS = 60_000;
const KUN_MS = 86_400_000;
/** Binance 4 soatlik shami: 00, 04, 08, 12, 16, 20 UTC. */
export const SHAM_SOAT = 4;
/** 1 kun = 6 ta rasmiy sessiya. */
export const KUNDAGI_SESSIYA = 24 / SHAM_SOAT;

export type Jadval = {
  /** A — shamdan necha daqiqa oldin */
  kashfiyotDaqiqa: number;
  /** B — shamdan necha daqiqa oldin (RASMIY sessiya) */
  tasdiqDaqiqa: number;
  /** B shundan keyin boshlanmasa — o'tkazib yuborilgan */
  tasdiqKechikishDaqiqa: number;
};

/** YAML (`radar:`) dagi standart qiymatlar bilan bir xil. */
export const STANDART_JADVAL: Jadval = {
  kashfiyotDaqiqa: 60,
  tasdiqDaqiqa: 15,
  tasdiqKechikishDaqiqa: 14,
};

/** `t` ichida turgan 4 soatlik shamning ochilishi (UTC). */
export function shamBoshi(t: Date): Date {
  const ms = t.getTime();
  return new Date(ms - (ms % (SHAM_SOAT * SOAT_MS)));
}

/** Kelajakdagi eng yaqin A va B sessiyalari.
 *
 * Pythondagi `keyingisi()` bilan BIR XIL: sessiya vaqti QAT'IY
 * `hozir` dan katta bo'lishi kerak. Ikki tomonda bir xil chegara
 * bo'lmasa, sahifa "keyingi sessiya 23:45" deb turgan paytda bot
 * o'sha sessiyani allaqachon boshlagan bo'lardi.
 */
export function keyingiSessiyalar(
  hozir: Date,
  j: Jadval = STANDART_JADVAL,
): { kashfiyot: Date; tasdiq: Date } {
  const boshi = shamBoshi(hozir).getTime();
  const keyingi = (daqiqa: number): Date => {
    // Uch sham oldinga qarash yetarli: daqiqa < 4 soat bo'lsa, eng
    // uzog'i ham keyingi ikkinchi shamga to'g'ri keladi.
    for (let k = 0; k <= 3; k++) {
      const vaqt = boshi + k * SHAM_SOAT * SOAT_MS - daqiqa * DAQIQA_MS;
      if (vaqt > hozir.getTime()) return new Date(vaqt);
    }
    return new Date(boshi + 4 * SHAM_SOAT * SOAT_MS - daqiqa * DAQIQA_MS);
  };
  return { kashfiyot: keyingi(j.kashfiyotDaqiqa), tasdiq: keyingi(j.tasdiqDaqiqa) };
}

/** Sham ochilishi -> `{kun, tartib}`. Kun — shamning UTC SANASI.
 *
 * 23:45 UTC dagi B sessiyasi keyingi kunning 00:00 shamiga tegishli,
 * ya'ni keyingi kunning 1-sessiyasi. Bishkekda kun shu sababli 05:45
 * da boshlanib 01:45 da tugaydi.
 */
export function kunVaTartib(shamVaqti: Date): { kun: string; tartib: number } {
  return {
    kun: shamVaqti.toISOString().slice(0, 10),
    tartib: Math.floor(shamVaqti.getUTCHours() / SHAM_SOAT) + 1,
  };
}

/** `(kun, tartib)` sessiyasi oldidan turgan sham ochilishi. */
export function shamVaqtiKunda(kun: string, tartib: number): Date {
  return new Date(kunBoshiMs(kun) + (tartib - 1) * SHAM_SOAT * SOAT_MS);
}

/** `(kun, tartib)` dagi B sessiyasining REJADAGI vaqti. */
export function tasdiqVaqti(kun: string, tartib: number, j: Jadval = STANDART_JADVAL): Date {
  return new Date(shamVaqtiKunda(kun, tartib).getTime() - j.tasdiqDaqiqa * DAQIQA_MS);
}

/** Hozir davom etayotgan kun — keyingi B sessiyasi tegishli kun.
 *
 * Kunning oxirgi (01:45) sessiyasidan keyin "bugun" allaqachon
 * keyingi kun bo'ladi: uning 1-sessiyasi hali oldinda.
 */
export function bugungiKun(hozir: Date, j: Jadval = STANDART_JADVAL): string {
  const { tasdiq } = keyingiSessiyalar(hozir, j);
  return kunVaTartib(new Date(tasdiq.getTime() + j.tasdiqDaqiqa * DAQIQA_MS)).kun;
}

/** Sahifa ochilganda tanlanadigan kun.
 *
 * Oxirgi TUGAGAN rasmiy sessiyaning kuni — ya'ni ekranda doim
 * ma'lumot bor kun. Radar hali yurmagan bo'lsa — keyingi B
 * sessiyasining kuni (bo'sh holat o'sha kunni tushuntiradi).
 */
export function joriyKun(
  oxirgiTasdiqKun: string | null,
  hozir: Date,
  j: Jadval = STANDART_JADVAL,
): string {
  if (oxirgiTasdiqKun && kunYaroqli(oxirgiTasdiqKun)) return oxirgiTasdiqKun;
  return bugungiKun(hozir, j);
}

/** `YYYY-MM-DD` haqiqiy sanami (31-fevral emas). */
export function kunYaroqli(xom: unknown): xom is string {
  if (typeof xom !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(xom)) return false;
  const d = new Date(`${xom}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === xom;
}

function kunBoshiMs(kun: string): number {
  return Date.parse(`${kun}T00:00:00Z`);
}

/** `kun` ga `n` kun qo'shish (manfiy — orqaga). */
export function kunQosh(kun: string, n: number): string {
  return new Date(kunBoshiMs(kun) + n * KUN_MS).toISOString().slice(0, 10);
}

/** Ikki kun orasidagi farq (kunda): `b - a`. */
export function kunFarqi(a: string, b: string): number {
  return Math.round((kunBoshiMs(b) - kunBoshiMs(a)) / KUN_MS);
}

/** `[boshi .. oxiri]` oralig'idagi hamma kun, o'sish tartibida. */
export function kunlarOraligi(boshi: string, oxiri: string): string[] {
  const natija: string[] = [];
  for (let k = boshi; k <= oxiri; k = kunQosh(k, 1)) natija.push(k);
  return natija;
}

// --------------------------------------------------------------------------- //
//  Oyna: 1 kun / 3 kun / 1 oy (10-bo'lim)
// --------------------------------------------------------------------------- //

export const ORALIQLAR = ["1k", "3k", "1o"] as const;
export type Oraliq = (typeof ORALIQLAR)[number];
/** Kunlar qatori va "1 oy" oynasi — 30 kundan eskisi ko'rsatilmaydi. */
export const KUNLAR_CHEGARASI = 30;

export function oraliqmi(x: unknown): x is Oraliq {
  return typeof x === "string" && (ORALIQLAR as readonly string[]).includes(x);
}

export function oraliqKunlari(oraliq: Oraliq): number {
  return oraliq === "1k" ? 1 : oraliq === "3k" ? 3 : KUNLAR_CHEGARASI;
}

/** Tanlangan kun bilan tugaydigan oyna kunlari. */
export function oynaKunlari(kun: string, oraliq: Oraliq): string[] {
  return kunlarOraligi(kunQosh(kun, -(oraliqKunlari(oraliq) - 1)), kun);
}

/** Kunlar qatori: `eng_yangi` dan 30 kun orqaga (yangisi birinchi). */
export function kunlarQatori(engYangi: string): string[] {
  return Array.from({ length: KUNLAR_CHEGARASI }, (_, i) => kunQosh(engYangi, -i));
}

// --------------------------------------------------------------------------- //
//  Bishkek vaqti — FAQAT `Intl` orqali
// --------------------------------------------------------------------------- //

export const STANDART_ZONA = "Asia/Bishkek";

const formatlagichlar = new Map<string, Intl.DateTimeFormat>();

/** Noto'g'ri yozilgan zona sahifani yiqitmasin — standartga qaytadi. */
export function zonaniTekshir(zona: unknown): string {
  if (typeof zona !== "string" || !zona) return STANDART_ZONA;
  try {
    new Intl.DateTimeFormat("en-GB", { timeZone: zona });
    return zona;
  } catch {
    return STANDART_ZONA;
  }
}

/** Vaqtning zonadagi qismlari.
 *
 * NEGA QO'LDA "+6" EMAS. Zona qoidasi o'zgarishi mumkin (yozgi vaqt
 * kiritilsa yoki YAML da boshqa zona yozilsa) — qo'lda qo'shilgan
 * soat o'shanda jimgina noto'g'ri bo'lib qoladi. `Intl` esa zona
 * bazasidan o'qiydi.
 */
export function vaqtQismlari(
  d: Date,
  zona: string,
): { yil: number; oy: number; kun: number; soat: number; daqiqa: number } {
  const z = zonaniTekshir(zona);
  let f = formatlagichlar.get(z);
  if (!f) {
    f = new Intl.DateTimeFormat("en-GB", {
      timeZone: z,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    });
    formatlagichlar.set(z, f);
  }
  const q: Record<string, number> = {};
  for (const p of f.formatToParts(d)) {
    if (p.type !== "literal") q[p.type] = Number(p.value);
  }
  return { yil: q.year, oy: q.month, kun: q.day, soat: q.hour % 24, daqiqa: q.minute };
}

const ikki = (n: number) => String(n).padStart(2, "0");

/** "13:45" — zonadagi soat. */
export function soatYoz(d: Date, zona: string): string {
  const q = vaqtQismlari(d, zona);
  return `${ikki(q.soat)}:${ikki(q.daqiqa)}`;
}

/** Zonadagi sana: `YYYY-MM-DD`. */
export function zonaSanasi(d: Date, zona: string): string {
  const q = vaqtQismlari(d, zona);
  return `${q.yil}-${ikki(q.oy)}-${ikki(q.kun)}`;
}

/** Matn shabloni: `"{n}-sessiya"` + `{n: 3}` -> `"3-sessiya"`.
 *  Tarjimada so'z tartibi tilga qarab o'zgaradi — shuning uchun
 *  matn bo'laklardan yopishtirilmaydi. */
export function shablon(matn: string, qiymatlar: Record<string, string | number>): string {
  return matn.replace(/\{([a-z_0-9]+)\}/gi, (butun, k: string) =>
    Object.hasOwn(qiymatlar, k) ? String(qiymatlar[k]) : butun,
  );
}

/** Sana yorlig'i: `14-okt` / `14 окт`.
 *  `oylar` — 12 ta qisqa oy nomi (tarjimadan), `andoza` — `"{k}-{o}"`. */
export function sanaYorligi(kun: string, oylar: string[], andoza: string): string {
  const [, oy, k] = kun.split("-").map(Number);
  return shablon(andoza, { k, o: oylar[oy - 1] ?? String(oy) });
}

/** Zonadagi to'liq vaqt yorlig'i: `14-okt 13:45`. */
export function vaqtYorligi(d: Date, zona: string, oylar: string[], andoza: string): string {
  return `${sanaYorligi(zonaSanasi(d, zona), oylar, andoza)} ${soatYoz(d, zona)}`;
}

// --------------------------------------------------------------------------- //
//  Baza qatorlari — tiplar
// --------------------------------------------------------------------------- //

export type TekshiruvKod = "hajm" | "narx" | "funding" | "oi" | "long_short" | "btc" | "taminot";
export type TekshiruvGuruh = "harakat" | "yoqilgi";
export type TekshiruvHolat = "ha" | "yoq" | "malumot_yoq";

/** 2-bosqichdagi tartib — kartochkada ham shu tartibda chiziladi. */
export const TEKSHIRUV_KODLARI: readonly TekshiruvKod[] = [
  "hajm",
  "narx",
  "funding",
  "oi",
  "long_short",
  "btc",
  "taminot",
];

/** Guruh — 5-bo'lim: harakat 1, 2, 6; yoqilg'i 3, 4, 5, 7. */
export const TEKSHIRUV_GURUHI: Record<TekshiruvKod, TekshiruvGuruh> = {
  hajm: "harakat",
  narx: "harakat",
  funding: "yoqilgi",
  oi: "yoqilgi",
  long_short: "yoqilgi",
  btc: "harakat",
  taminot: "yoqilgi",
};

export type Tekshiruv = {
  kod: TekshiruvKod;
  guruh: TekshiruvGuruh;
  holat: TekshiruvHolat;
  qiymat: number | null;
  chegara: number | null;
  manba: string;
  qoshimcha: Record<string, unknown>;
};

export type ManbaHolati = {
  nom: string;
  holat: "ok" | "xato";
  kod: number | null;
  izoh: string;
};

export type Sessiya = {
  id: number;
  turi: string;
  shamVaqti: Date | null;
  kun: string;
  tartib: number;
  boshlandi: Date | null;
  tugadi: Date | null;
  /** `yurmoqda` | `tugadi` | `xato` */
  holat: string;
  universum: number;
  darvozadan: number;
  elakdan: number;
  nomzod: number;
  btcOzgarish: number | null;
  manbalar: ManbaHolati[];
  sozlama: Partial<Record<SozlamaKalit, number>>;
  izoh: string;
};

/** Grafik va jadval uchun yetarli — sessiyaning qisqa ko'rinishi. */
export type SessiyaQisqa = Pick<Sessiya, "id" | "kun" | "tartib" | "holat">;

export type CoinHolati = "tasdiqlangan" | "vaqtinchalik" | "nomzod" | "oddiy";
export type HalolHolati = "halol" | "harom" | "shubhali" | "baholanmagan";

export type Natija = {
  sessiyaId: number;
  symbol: string;
  belgi: string;
  /** `elak` | `namuna` | `chiqdi` */
  turi: string;
  /** O'sha sessiyadagi narx — kirish uchun tavsiya EMAS */
  narx: number | null;
  hajm24s: number | null;
  hajmNisbati: number | null;
  ozgarish24s: number | null;
  marketCap: number | null;
  tekshiruvlar: Tekshiruv[];
  tasdiqSoni: number;
  harakatSoni: number;
  yoqilgiSoni: number;
  malumotYoqSoni: number;
  nomzod: boolean;
  holat: CoinHolati;
  orin: number | null;
  ketmaKet: number;
  yashirin: boolean;
  yangiListing: boolean;
  halol: HalolHolati;
};

/** Grafik va jadval uchun — o'nlab sessiya, minglab qator. */
export type YengilNatija = Pick<
  Natija,
  "sessiyaId" | "symbol" | "belgi" | "turi" | "orin" | "narx" | "holat"
>;

/** Calibration qatori — faqat baholangan maydonlar. */
export type KalibrQator = {
  turi: string;
  nomzod: boolean;
  tasdiqSoni: number;
  tekshiruvlar: Tekshiruv[];
  kel24Max: number | null;
  kel24Min: number | null;
  kel7Max: number | null;
  kel7Min: number | null;
};

// --------------------------------------------------------------------------- //
//  JSON ni xavfsiz o'qish
// --------------------------------------------------------------------------- //

/** Buzuq JSON BUTUN SAHIFANI yiqitmasin (`queries.ts` dagi
 *  `jsonRoyxat` bilan bir xil qoida) — o'sha qism bo'sh chiqadi. */
export function jsonRoyxat<T = unknown>(xom: unknown): T[] {
  try {
    const natija = JSON.parse(String(xom ?? "[]")) as unknown;
    return Array.isArray(natija) ? (natija as T[]) : [];
  } catch {
    return [];
  }
}

function jsonObyekt(xom: unknown): Record<string, unknown> {
  try {
    const natija = JSON.parse(String(xom ?? "{}")) as unknown;
    return natija && typeof natija === "object" && !Array.isArray(natija)
      ? (natija as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function sonYoki(x: unknown): number | null {
  if (typeof x === "number") return Number.isFinite(x) ? x : null;
  if (typeof x === "string" && x.trim() !== "") {
    const n = Number(x);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

/** `tekshiruvlar_json` -> 7 ta tekshiruv, kanonik tartibda.
 *
 * Har element ALOHIDA tekshiriladi: bitta buzuq element qolganlarini
 * yo'qotmasin. Noma'lum `kod` tashlanadi, noma'lum `holat` esa
 * "ma'lumot yo'q" deb o'qiladi — bilmagan narsani ✅ deb ko'rsatish
 * yolg'on bo'lardi.
 */
export function tekshiruvlarniOqi(xom: unknown): Tekshiruv[] {
  const natija: Tekshiruv[] = [];
  const korilgan = new Set<string>();
  for (const el of jsonRoyxat<unknown>(xom)) {
    if (!el || typeof el !== "object") continue;
    const e = el as Record<string, unknown>;
    const kod = e.kod;
    if (typeof kod !== "string" || !(TEKSHIRUV_KODLARI as readonly string[]).includes(kod)) {
      continue;
    }
    if (korilgan.has(kod)) continue;
    korilgan.add(kod);
    const k = kod as TekshiruvKod;
    const holat: TekshiruvHolat =
      e.holat === "ha" || e.holat === "yoq" ? e.holat : "malumot_yoq";
    const qoshimcha =
      e.qoshimcha && typeof e.qoshimcha === "object" && !Array.isArray(e.qoshimcha)
        ? (e.qoshimcha as Record<string, unknown>)
        : {};
    natija.push({
      kod: k,
      guruh: e.guruh === "harakat" || e.guruh === "yoqilgi" ? e.guruh : TEKSHIRUV_GURUHI[k],
      holat,
      qiymat: sonYoki(e.qiymat),
      chegara: sonYoki(e.chegara),
      manba: typeof e.manba === "string" ? e.manba : "",
      qoshimcha,
    });
  }
  return natija.sort(
    (a, b) => TEKSHIRUV_KODLARI.indexOf(a.kod) - TEKSHIRUV_KODLARI.indexOf(b.kod),
  );
}

/** `manbalar_json` -> manbalar ro'yxati. */
export function manbalarniOqi(xom: unknown): ManbaHolati[] {
  return Object.entries(jsonObyekt(xom)).map(([nom, v]) => {
    const e = v && typeof v === "object" ? (v as Record<string, unknown>) : {};
    const kod = sonYoki(e.kod);
    return {
      nom,
      holat: e.holat === "ok" ? "ok" : "xato",
      kod: kod === null ? null : Math.trunc(kod),
      izoh: typeof e.izoh === "string" ? e.izoh : "",
    };
  });
}

/** HTTP 451 — server mintaqasi Binance tomonidan cheklangan.
 *  Bu "vaqtincha xato" emas: shu serverdan ma'lumot UMUMAN kelmaydi. */
export function mintaqaCheklanganmi(manbalar: ManbaHolati[]): boolean {
  return manbalar.some((m) => m.kod === 451);
}

// --------------------------------------------------------------------------- //
//  Kartochka matni
// --------------------------------------------------------------------------- //

/** "5/7 · Harakat 3/3 · Yoqilg'i 2/4" uchun sanoq.
 *  Maxrajlar tekshiruvlarning o'zidan — ro'yxat buzuq bo'lsa ham
 *  5-bo'limdagi 3 va 4 ga qaytadi. */
export function sanoq(n: Pick<Natija, "tekshiruvlar" | "tasdiqSoni" | "harakatSoni" | "yoqilgiSoni">): {
  jami: number;
  jamiMax: number;
  harakat: number;
  harakatMax: number;
  yoqilgi: number;
  yoqilgiMax: number;
} {
  const harakatMax = n.tekshiruvlar.length
    ? n.tekshiruvlar.filter((t) => t.guruh === "harakat").length
    : 3;
  const yoqilgiMax = n.tekshiruvlar.length
    ? n.tekshiruvlar.filter((t) => t.guruh === "yoqilgi").length
    : 4;
  return {
    jami: n.tasdiqSoni,
    jamiMax: n.tekshiruvlar.length || TEKSHIRUV_KODLARI.length,
    harakat: n.harakatSoni,
    harakatMax,
    yoqilgi: n.yoqilgiSoni,
    yoqilgiMax,
  };
}

/** Raqam: kasr qismi bilan, manfiy belgi — haqiqiy minus (−). */
export function sonYoz(x: number, xona = 1): string {
  const m = x.toFixed(xona);
  return m.startsWith("-") ? `−${m.slice(1)}` : m;
}

/** Ishorali foiz: `+287%`, `−0.34%`. Nol — ishorasiz. */
export function ishoraliFoiz(x: number, xona = 1): string {
  const yaxlit = Number(x.toFixed(xona));
  if (yaxlit === 0) return `${(0).toFixed(xona)}%`;
  return `${yaxlit > 0 ? "+" : ""}${sonYoz(x, xona)}%`;
}

/** Ishorali son (punkt uchun): `+287.7`, `−12.0`. */
export function ishoraliSon(x: number, xona = 1): string {
  const yaxlit = Number(x.toFixed(xona));
  if (yaxlit === 0) return (0).toFixed(xona);
  return `${yaxlit > 0 ? "+" : ""}${sonYoz(x, xona)}`;
}

/** Ixcham son: ortiqcha nollarsiz. `0.3400` -> "0.34", `41.0` -> "41",
 *  `-2.5` -> "−2.5". `xona` — eng ko'p kasr xonasi. */
export function ixchamSon(x: number, xona = 2): string {
  const yaxlit = Number(x.toFixed(xona));
  const m = String(Object.is(yaxlit, -0) ? 0 : yaxlit);
  return m.startsWith("-") ? `−${m.slice(1)}` : m;
}

/** Ixcham ishorali foiz: "+287%", "−0.34%", "+41%". */
export function ixchamFoiz(x: number, xona = 2): string {
  const m = ixchamSon(x, xona);
  return `${m !== "0" && !m.startsWith("−") ? "+" : ""}${m}%`;
}

/** Foiz uchun mos aniqlik: katta qiymatda kasr shovqin. */
function foizXonasi(x: number): number {
  const a = Math.abs(x);
  return a >= 100 ? 0 : a >= 10 ? 1 : 2;
}

/** Tekshiruv izohining shabloni va qiymatlari.
 *
 * Matnning O'ZI tarjimada (`radar.sabab.*`): bu yerda faqat qaysi
 * shablon va unga qaysi raqamlar. Shunda bitta mantiq ikki tilda
 * bir xil ishlaydi va testda bazasiz tekshiriladi.
 */
export function tekshiruvSababi(t: Tekshiruv): {
  kalit: string;
  qiymatlar: Record<string, string>;
} {
  const q = t.qiymat;
  const c = t.chegara;
  const qo = t.qoshimcha;
  // Chegara doim musbat ko'rsatiladi: ishorasi shablonda ("±", "+").
  const cYoz = () => (c === null ? "—" : ixchamSon(Math.abs(c), 4));
  switch (t.kod) {
    case "hajm": {
      if (q === null) return { kalit: "hajm_yoq", qiymatlar: {} };
      const kunlar = sonYoki(qo.kunlar);
      return {
        kalit: kunlar ? "hajm_kunlar" : "hajm",
        qiymatlar: { x: ixchamSon(q, 1), c: cYoz(), k: kunlar ? String(Math.round(kunlar)) : "" },
      };
    }
    case "narx":
      if (q === null) return { kalit: "narx_yoq", qiymatlar: {} };
      return { kalit: "narx", qiymatlar: { x: ixchamFoiz(q, foizXonasi(q)), c: cYoz() } };
    case "funding": {
      if (q === null) return { kalit: "funding_yoq", qiymatlar: {} };
      const oraliq = sonYoki(qo.oraliq_soat);
      const x = ixchamFoiz(q, 4);
      // Tabiiy 8 soatlik oraliqda "keltirilgan" izohi ortiqcha.
      if (oraliq !== null && oraliq !== 8) {
        return { kalit: "funding_oraliq", qiymatlar: { x, o: ixchamSon(oraliq, 2), c: cYoz() } };
      }
      return { kalit: "funding", qiymatlar: { x, c: cYoz() } };
    }
    case "oi": {
      const soat = sonYoki(qo.soat);
      // Tarix bor, lekin 8 soatlik oyna to'lmagan (yangi listing): bot
      // ataylab ⚪ beradi — birinchi soatning OI si ~0 bo'lib, "+800%"
      // chiqardi. Bu "tarix yo'q" emas, shuning uchun alohida matn.
      if (q === null && soat !== null && soat > 0) {
        return { kalit: "oi_qisqa", qiymatlar: { s: ixchamSon(soat, 1) } };
      }
      if (q === null) return { kalit: "oi_yoq", qiymatlar: {} };
      return {
        kalit: "oi",
        qiymatlar: { s: ixchamSon(soat ?? 8, 1), x: ixchamFoiz(q, foizXonasi(q)), c: cYoz() },
      };
    }
    case "long_short": {
      if (q === null || q <= 0) return { kalit: "long_short_yoq", qiymatlar: {} };
      // Og'ish — qaysi tomonga bo'lsa ham: 0.4 = "1:2.5" (short ko'p).
      if (q >= 1) {
        return { kalit: "long_short_long", qiymatlar: { r: sonYoz(q, 1), c: cYoz() } };
      }
      return { kalit: "long_short_short", qiymatlar: { r: sonYoz(1 / q, 1), c: cYoz() } };
    }
    case "btc":
      if (q === null) return { kalit: "btc_yoq", qiymatlar: {} };
      return { kalit: "btc", qiymatlar: { x: ishoraliSon(q, 1), c: cYoz() } };
    case "taminot": {
      const aylanma = sonYoki(qo.aylanma_pct) ?? q;
      const unlockKun = sonYoki(qo.unlock_kun);
      const unlockPct = sonYoki(qo.unlock_pct);
      const k = unlockKun === null ? "" : String(Math.round(unlockKun));
      const a = aylanma === null ? "" : sonYoz(aylanma, 1);
      if (aylanma === null && unlockPct === null) {
        return { kalit: "taminot_yoq", qiymatlar: {} };
      }
      if (aylanma === null) {
        return { kalit: "taminot_faqat_unlock", qiymatlar: { k, u: ixchamSon(unlockPct ?? 0, 1) } };
      }
      if (unlockPct !== null && unlockPct > 0) {
        return { kalit: "taminot_unlock", qiymatlar: { a, k, u: ixchamSon(unlockPct, 1) } };
      }
      return { kalit: unlockKun === null ? "taminot" : "taminot_unlock_yoq", qiymatlar: { a, k } };
    }
  }
}

/** XULOSA uchun: qaysi tekshiruvlar tasdiqlandi — guruhlarga bo'lib. */
export function xulosaQismlari(tekshiruvlar: Tekshiruv[]): {
  harakat: TekshiruvKod[];
  yoqilgi: TekshiruvKod[];
} {
  const otgan = tekshiruvlar.filter((t) => t.holat === "ha");
  return {
    harakat: otgan.filter((t) => t.guruh === "harakat").map((t) => t.kod),
    yoqilgi: otgan.filter((t) => t.guruh === "yoqilgi").map((t) => t.kod),
  };
}

/** Kapitalizatsiya / hajm: `$12.3M`, `$1.20B`. */
export function qisqaPul(n: number | null): string | null {
  if (n === null || !Number.isFinite(n)) return null;
  const a = Math.abs(n);
  if (a >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

/** Coin narxi — arzon coinlarda ko'proq xona (`format.ts/narx` bilan
 *  bir xil mantiq; bu fayl sof qolishi uchun alohida). */
export function narxYoz(n: number | null): string | null {
  if (n === null || !Number.isFinite(n)) return null;
  const a = Math.abs(n);
  const xona = a >= 1000 ? 2 : a >= 1 ? 4 : a >= 0.01 ? 6 : 8;
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: xona });
}

// --------------------------------------------------------------------------- //
//  Ustunlar — grafik va jadval uchun umumiy o'q
// --------------------------------------------------------------------------- //

export type Ustun = {
  /** `kun#tartib` (sessiya) yoki `kun` (oylik ko'rinish) */
  kalit: string;
  kun: string;
  /** Oylik ko'rinishda `null` */
  tartib: number | null;
  /** Rejadagi vaqt (oylikda — kunning 1-sessiyasi) */
  vaqt: Date;
  /** `bor` ustundagi sessiya; oylikda — `null` */
  sessiyaId: number | null;
  /** `otkazildi` — vaqti o'tgan, lekin natija yo'q (bo'sh ustun) */
  holat: "bor" | "otkazildi";
};

/** Sessiya qancha vaqtdan keyin "osilib qolgan" hisoblanadi.
 *  Ishchi sessiya o'rtasida o'chsa, `yurmoqda` qator abadiy qoladi —
 *  bir soatdan keyin u o'tkazib yuborilgan deb ko'rsatiladi. */
const OSILGAN_DAQIQA = 60;

/** Oyna kunlari -> rasmiy sessiya ustunlari.
 *
 *   tugagan sessiya bor          -> `bor`
 *   xato bilan tugagan / osilgan -> `otkazildi`
 *   yo'q, kechikish muddati o'tgan -> `otkazildi` (sun'iy to'ldirilmaydi)
 *   hali vaqti kelmagan / yurmoqda -> ustun YO'Q (varaq o'ngga o'sadi)
 */
export function sessiyaUstunlari(
  kunlar: string[],
  sessiyalar: SessiyaQisqa[],
  hozir: Date,
  j: Jadval = STANDART_JADVAL,
): Ustun[] {
  const guruh = new Map<string, SessiyaQisqa[]>();
  for (const s of sessiyalar) {
    const k = `${s.kun}#${s.tartib}`;
    guruh.set(k, [...(guruh.get(k) ?? []), s]);
  }
  const natija: Ustun[] = [];
  for (const kun of kunlar) {
    for (let tartib = 1; tartib <= KUNDAGI_SESSIYA; tartib++) {
      const kalit = `${kun}#${tartib}`;
      const vaqt = tasdiqVaqti(kun, tartib, j);
      const bular = guruh.get(kalit) ?? [];
      // Bir slotda ikki yozuv bo'lsa (qayta ishga tushirish) — eng yangisi.
      const tugagan = bular
        .filter((s) => s.holat === "tugadi")
        .sort((a, b) => b.id - a.id)[0];
      if (tugagan) {
        natija.push({ kalit, kun, tartib, vaqt, sessiyaId: tugagan.id, holat: "bor" });
        continue;
      }
      const ms = hozir.getTime();
      const yurmoqda = bular.some((s) => s.holat === "yurmoqda");
      const xato = bular.some((s) => s.holat === "xato");
      const muddat = vaqt.getTime() + j.tasdiqKechikishDaqiqa * DAQIQA_MS;
      const osilgan = vaqt.getTime() + OSILGAN_DAQIQA * DAQIQA_MS;
      const otkazildi = xato || (yurmoqda ? ms > osilgan : ms > muddat);
      if (otkazildi) {
        natija.push({ kalit, kun, tartib, vaqt, sessiyaId: null, holat: "otkazildi" });
      }
    }
  }
  return natija;
}

/** "1 oy" ko'rinishi: har kun bitta ustun. */
export function kunUstunlari(
  kunlar: string[],
  sessiyalar: SessiyaQisqa[],
  hozir: Date,
  j: Jadval = STANDART_JADVAL,
): Ustun[] {
  const tugagan = new Set(sessiyalar.filter((s) => s.holat === "tugadi").map((s) => s.kun));
  const natija: Ustun[] = [];
  for (const kun of kunlar) {
    const vaqt = tasdiqVaqti(kun, 1, j);
    if (tugagan.has(kun)) {
      natija.push({ kalit: kun, kun, tartib: null, vaqt, sessiyaId: null, holat: "bor" });
    } else if (hozir.getTime() > vaqt.getTime() + j.tasdiqKechikishDaqiqa * DAQIQA_MS) {
      natija.push({ kalit: kun, kun, tartib: null, vaqt, sessiyaId: null, holat: "otkazildi" });
    }
  }
  return natija;
}

/** Radar ishga tushishidan OLDINGI ustunlarni olib tashlaydi.
 *
 * "O'tkazib yuborildi" — bot o'chiq bo'lgan sessiya. Radar hali
 * umuman mavjud bo'lmagan kunlarni shunday belgilash yolg'on bo'lardi:
 * birinchi oy grafigi 25 ta bo'sh ustun bilan boshlanardi.
 * `birinchi` — eng birinchi rasmiy sessiya (har qanday holatda).
 */
export function boshlanishdanKeyin(
  ustunlar: Ustun[],
  birinchi: { kun: string; tartib: number } | null,
): Ustun[] {
  if (!birinchi) return [];
  return ustunlar.filter((u) =>
    u.tartib === null
      ? u.kun >= birinchi.kun
      : u.kun > birinchi.kun || (u.kun === birinchi.kun && u.tartib >= birinchi.tartib),
  );
}

// --------------------------------------------------------------------------- //
//  Grafik — o'rin oqimi (bump chart)
// --------------------------------------------------------------------------- //

/** Bitta ustundagi coin holati.
 *
 *   orin       — Top-N ichida, shu o'rinda chiziladi
 *   tashqarida — pool ichida, lekin Top-N dan pastda (#13 kabi)
 *   chiqdi     — oldingi ustunda bor edi, endi pooldan ham tushdi
 *   bosh       — sessiya o'tkazib yuborilgan: chiziq UZILADI
 *   yoq        — oynada hali paydo bo'lmagan / chiqib ketgandan keyin
 *                qaytmagan: hech narsa chizilmaydi
 */
export type BumpNuqta =
  | { tur: "orin"; orin: number }
  | { tur: "tashqarida"; orin: number }
  | { tur: "chiqdi" }
  | { tur: "bosh" }
  | { tur: "yoq" };

export type BumpSeriya = {
  symbol: string;
  belgi: string;
  /** Rang/chiziq tartibi — eng yaxshi o'rin bo'yicha */
  tartib: number;
  nuqtalar: BumpNuqta[];
};

/** Ustundagi bitta coin — sessiya qatori yoki kunlik agregat. */
export type UstunQatori = {
  symbol: string;
  belgi: string;
  turi: string;
  orin: number | null;
};

/** Umumiy shakllantirish: ustunlar + har ustundagi qatorlar.
 *
 * Grafikka FAQAT oynada kamida bir marta Top-N ga kirgan coin
 * chiziladi (10-bo'lim). "chiqdi" — faqat bevosita oldingi mavjud
 * ustunda pool ichida bo'lgan coinga (yoki baza `chiqdi` deb yozgan
 * qatorga). Oynada hali paydo bo'lmagan coinni "chiqdi" zonasidan
 * boshlash yolg'on bo'lardi: u chiqmagan, u hali kirmagan edi.
 */
export function bumpQur(
  ustunlar: Ustun[],
  qatorlar: Map<string, UstunQatori[]>,
  topN: number,
): BumpSeriya[] {
  const indeks = new Map<string, Map<string, UstunQatori>>();
  const belgilar = new Map<string, string>();
  const engYaxshi = new Map<string, number>();
  for (const u of ustunlar) {
    if (u.holat !== "bor") continue;
    const m = new Map<string, UstunQatori>();
    for (const q of qatorlar.get(u.kalit) ?? []) {
      m.set(q.symbol, q);
      if (q.turi === "elak" && q.orin !== null && q.orin <= topN) {
        belgilar.set(q.symbol, q.belgi);
        engYaxshi.set(q.symbol, Math.min(engYaxshi.get(q.symbol) ?? Infinity, q.orin));
      }
    }
    indeks.set(u.kalit, m);
  }

  const symbollar = [...engYaxshi.keys()].sort(
    (a, b) => engYaxshi.get(a)! - engYaxshi.get(b)! || a.localeCompare(b),
  );

  return symbollar.map((symbol, tartib) => {
    let oldingiBor = false;
    const nuqtalar = ustunlar.map((u): BumpNuqta => {
      if (u.holat !== "bor") return { tur: "bosh" };
      const q = indeks.get(u.kalit)?.get(symbol);
      if (q && q.turi === "elak" && q.orin !== null) {
        oldingiBor = true;
        return q.orin <= topN ? { tur: "orin", orin: q.orin } : { tur: "tashqarida", orin: q.orin };
      }
      const chiqdi = q?.turi === "chiqdi" || oldingiBor;
      oldingiBor = false;
      return chiqdi ? { tur: "chiqdi" } : { tur: "yoq" };
    });
    return { symbol, belgi: belgilar.get(symbol) ?? symbol, tartib, nuqtalar };
  });
}

/** Sessiya ko'rinishi (1 kun / 3 kun). */
export function sessiyaBump(ustunlar: Ustun[], natijalar: YengilNatija[], topN: number): BumpSeriya[] {
  return bumpQur(ustunlar, sessiyaQatorlari(ustunlar, natijalar), topN);
}

function sessiyaQatorlari(ustunlar: Ustun[], natijalar: YengilNatija[]): Map<string, UstunQatori[]> {
  const idDan = new Map<number, string>();
  for (const u of ustunlar) if (u.sessiyaId !== null) idDan.set(u.sessiyaId, u.kalit);
  const natija = new Map<string, UstunQatori[]>();
  for (const n of natijalar) {
    const kalit = idDan.get(n.sessiyaId);
    if (!kalit) continue;
    const r = natija.get(kalit) ?? [];
    r.push({ symbol: n.symbol, belgi: n.belgi, turi: n.turi, orin: n.orin });
    natija.set(kalit, r);
  }
  return natija;
}

/** Bir kunning umumiy o'rni (B-variant, 10-bo'lim).
 *
 * Kun davomida Top-N da ENG KO'P turgan coinlar yuqorida; teng
 * bo'lsa — o'sha sessiyalardagi o'rtacha o'rni kichigi; keyin
 * symbol (natija har doim bir xil chiqsin). Bitta g'alati sessiya
 * kunni buzmaydi.
 *
 * Top-N ga hech kirmagan, lekin kunda o'rin olgan coinlar ham
 * tartiblanadi (o'rtacha o'rni bo'yicha) — ular grafikda "Top-N dan
 * tashqari" zonasida o'z kunlik raqami bilan turadi.
 *
 * Qaytadi: symbol -> kunlik o'rin (1 dan).
 */
export function kunlikOrinlar(
  natijalar: Pick<YengilNatija, "symbol" | "turi" | "orin">[],
  topN: number,
): Map<string, number> {
  const yigma = new Map<string, { topda: number; topYig: number; hammaYig: number; hamma: number }>();
  for (const n of natijalar) {
    if (n.turi !== "elak" || n.orin === null) continue;
    const y = yigma.get(n.symbol) ?? { topda: 0, topYig: 0, hammaYig: 0, hamma: 0 };
    y.hamma += 1;
    y.hammaYig += n.orin;
    if (n.orin <= topN) {
      y.topda += 1;
      y.topYig += n.orin;
    }
    yigma.set(n.symbol, y);
  }
  const ortacha = (y: { topda: number; topYig: number; hammaYig: number; hamma: number }) =>
    y.topda > 0 ? y.topYig / y.topda : y.hammaYig / y.hamma;
  const tartib = [...yigma.entries()].sort(
    ([sa, a], [sb, b]) => b.topda - a.topda || ortacha(a) - ortacha(b) || sa.localeCompare(sb),
  );
  return new Map(tartib.map(([s], i) => [s, i + 1]));
}

/** "1 oy" ko'rinishi: har kun — kunlik o'rin bilan bitta ustun. */
export function oylikBump(
  ustunlar: Ustun[],
  sessiyalar: SessiyaQisqa[],
  natijalar: YengilNatija[],
  topN: number,
): BumpSeriya[] {
  const kunDan = new Map<number, string>();
  for (const s of sessiyalar) if (s.holat === "tugadi") kunDan.set(s.id, s.kun);
  const kunlik = new Map<string, YengilNatija[]>();
  for (const n of natijalar) {
    const kun = kunDan.get(n.sessiyaId);
    if (!kun) continue;
    kunlik.set(kun, [...(kunlik.get(kun) ?? []), n]);
  }
  const qatorlar = new Map<string, UstunQatori[]>();
  for (const u of ustunlar) {
    const bular = kunlik.get(u.kun) ?? [];
    const belgi = new Map(bular.map((n) => [n.symbol, n.belgi]));
    const orinlar = kunlikOrinlar(bular, topN);
    qatorlar.set(
      u.kalit,
      [...orinlar.entries()].map(([symbol, orin]) => ({
        symbol,
        belgi: belgi.get(symbol) ?? symbol,
        turi: "elak",
        orin,
      })),
    );
  }
  return bumpQur(ustunlar, qatorlar, topN);
}

/** Grafik ranglari — kategoriya palitrasi, QAT'IY TARTIBDA.
 *
 * Qorong'i variant `dataviz` tavsiyasidagi tekshirilgan to'plam: sahifa
 * foni (`--rang-fon`, #0a2450) ustida hamma tekshiruvdan o'tgan
 * (`validate_palette.js --mode dark --surface #0a2450`: rang ko'rligi
 * uchun qo'shnilar ΔE ≥ 8.4, oddiy ko'z ΔE ≥ 19.3, kontrast ≥ 3:1).
 * Grafik shu sababli panel ichida, `bg-fon` yuzasida chiziladi.
 *
 * 8 tadan ko'p coin bo'lsa rang YANGI ishlab chiqarilmaydi: rang
 * qaytadan boshlanadi, lekin chiziq shakli o'zgaradi (uzuq, nuqtali).
 * Bundan tashqari har chiziqning ikki uchida coin nomi yozilgan —
 * rang hech qachon yagona belgi emas.
 */
export const SERIYA_RANGLARI = [
  "#3987e5",
  "#d95926",
  "#199e70",
  "#c98500",
  "#d55181",
  "#008300",
  "#9085e9",
  "#e66767",
] as const;

const SERIYA_CHIZIQLARI = [undefined, "6 4", "1.5 3.5"] as const;

export function seriyaUslubi(tartib: number): { rang: string; chiziq: string | undefined } {
  const n = SERIYA_RANGLARI.length;
  return {
    rang: SERIYA_RANGLARI[tartib % n],
    chiziq: SERIYA_CHIZIQLARI[Math.floor(tartib / n) % SERIYA_CHIZIQLARI.length],
  };
}

// --------------------------------------------------------------------------- //
//  Sessiya jadvali (10-bo'lim)
// --------------------------------------------------------------------------- //

export type JadvalKatak =
  | { tur: "otkazildi" }
  | { tur: "orin"; orin: number; foiz: number | null; tasdiqlangan: boolean }
  | { tur: "chiqdi"; foiz: number | null }
  /** Pool ichida, lekin o'rin olmagan (admin yashirgan) */
  | { tur: "orinsiz"; foiz: number | null }
  | { tur: "yoq" };

export type JadvalQatori = {
  symbol: string;
  belgi: string;
  kataklar: JadvalKatak[];
};

/** Jadval qatorlari.
 *
 * QATORLAR: oynada Top-N ga kirgan coinlar + oynadan BEVOSITA oldingi
 * rasmiy sessiyada Top-N da bo'lganlar (ular birinchi ustunda
 * "chiqdi" bo'lib ko'rinishi mumkin).
 *
 * FOIZ: shu sessiyadagi narx / bevosita oldingi MAVJUD rasmiy
 * sessiyadagi narx − 1. Kunning 1-sessiyasi kechagi oxirgisidan
 * hisoblanadi — kunlar narx orqali bog'lanadi. Foiz FAQAT coin
 * oldingi sessiyada o'rin olgan bo'lsa yoziladi (o'rin qanday
 * bo'lsa ham): aks holda "qayerdan hisoblandi" degan savolga javob
 * bo'lmasdi.
 *
 * `oldingiSessiyaId` — oynaning birinchi mavjud ustunidan oldingi
 * rasmiy sessiya (u oldingi kunda bo'lishi mumkin).
 */
export function sessiyaJadvali(
  ustunlar: Ustun[],
  natijalar: YengilNatija[],
  oldingiSessiyaId: number | null,
  topN: number,
): JadvalQatori[] {
  const sessiyaDan = new Map<number, Map<string, YengilNatija>>();
  for (const n of natijalar) {
    const m = sessiyaDan.get(n.sessiyaId) ?? new Map<string, YengilNatija>();
    m.set(n.symbol, n);
    sessiyaDan.set(n.sessiyaId, m);
  }
  const topda = (n: YengilNatija | undefined) =>
    !!n && n.turi === "elak" && n.orin !== null && n.orin <= topN;

  const belgilar = new Map<string, string>();
  const qoshish = (id: number | null) => {
    if (id === null) return;
    for (const n of sessiyaDan.get(id)?.values() ?? []) {
      if (topda(n)) belgilar.set(n.symbol, n.belgi);
    }
  };
  qoshish(oldingiSessiyaId);
  for (const u of ustunlar) if (u.holat === "bor") qoshish(u.sessiyaId);

  // Har ustun uchun "oldingi mavjud sessiya"
  const oldingilar: (number | null)[] = [];
  let oxirgi = oldingiSessiyaId;
  for (const u of ustunlar) {
    oldingilar.push(oxirgi);
    if (u.holat === "bor") oxirgi = u.sessiyaId;
  }

  const qatorlar = [...belgilar.entries()].map(([symbol, belgi]): JadvalQatori => ({
    symbol,
    belgi,
    kataklar: ustunlar.map((u, i): JadvalKatak => {
      if (u.holat !== "bor" || u.sessiyaId === null) return { tur: "otkazildi" };
      const n = sessiyaDan.get(u.sessiyaId)?.get(symbol);
      if (!n) return { tur: "yoq" };
      const oldingiId = oldingilar[i];
      const o = oldingiId === null ? undefined : sessiyaDan.get(oldingiId)?.get(symbol);
      const foiz =
        o && o.orin !== null && o.narx !== null && o.narx > 0 && n.narx !== null
          ? (n.narx / o.narx - 1) * 100
          : null;
      if (n.turi === "chiqdi") return { tur: "chiqdi", foiz };
      if (n.turi !== "elak") return { tur: "yoq" };
      if (n.orin === null) return { tur: "orinsiz", foiz };
      return { tur: "orin", orin: n.orin, foiz, tasdiqlangan: n.holat === "tasdiqlangan" };
    }),
  }));

  // Tartib: oxirgi mavjud ustundagi o'rin, keyin oynadagi eng yaxshi
  // o'rin, keyin symbol — jadval har safar bir xil ko'rinsin.
  const oxirgiUstun = ustunlar.map((u) => u.holat).lastIndexOf("bor");
  const orinOl = (q: JadvalQatori, i: number) => {
    const k = q.kataklar[i];
    return k && k.tur === "orin" ? k.orin : Infinity;
  };
  const engYaxshi = (q: JadvalQatori) =>
    Math.min(Infinity, ...q.kataklar.map((k) => (k.tur === "orin" ? k.orin : Infinity)));
  return qatorlar.sort(
    (a, b) =>
      (oxirgiUstun >= 0 ? orinOl(a, oxirgiUstun) - orinOl(b, oxirgiUstun) : 0) ||
      engYaxshi(a) - engYaxshi(b) ||
      a.symbol.localeCompare(b.symbol),
  );
}

// --------------------------------------------------------------------------- //
//  Calibration (11-bo'lim)
// --------------------------------------------------------------------------- //

/** Shundan kam namunada ulush ishonchsiz — sahifa ogohlantiradi. */
export const KAM_NAMUNA = 30;

export type KalibrGuruhKod = "nomzod" | "nomzod_emas" | "namuna";
export const KALIBR_GURUHLARI: readonly KalibrGuruhKod[] = ["nomzod", "nomzod_emas", "namuna"];

export type Ulush = { n: number; portlash: number; ulush: number | null };

export type KalibrGuruh = {
  kun24: Ulush;
  kun7: Ulush;
  /** 24 soatdagi eng yuqori o'sish / eng chuqur tushish — o'rtacha */
  ortachaMax24: number | null;
  ortachaMin24: number | null;
  /** `n < KAM_NAMUNA` — ulush hali hech narsa demaydi */
  kam: boolean;
};

export type KalibrTekshiruv = {
  ha: { kun24: Ulush; kun7: Ulush };
  yoq: { kun24: Ulush; kun7: Ulush };
  malumotYoq: number;
};

export type Kalibrovka = {
  jami24: number;
  jami7: number;
  guruhlar: Record<KalibrGuruhKod, KalibrGuruh>;
  tekshiruvlar: Record<TekshiruvKod, KalibrTekshiruv>;
  /** Tasdiq soni 0..7 bo'yicha */
  tasdiqSoni: { soni: number; kun24: Ulush; kun7: Ulush }[];
};

function ulushHisobla(n: number, portlash: number): Ulush {
  return { n, portlash, ulush: n > 0 ? (portlash / n) * 100 : null };
}

function ortacha(qiymatlar: number[]): number | null {
  return qiymatlar.length ? qiymatlar.reduce((a, b) => a + b, 0) / qiymatlar.length : null;
}

/** Calibration hisobi — FAQAT rasmiy sessiyalarning `elak` va
 *  `namuna` qatorlari (sahifa shuni o'qiydi).
 *
 * "Portlash": 24 soatda eng yuqori o'sish ≥ `portlash24`, 7 kunda
 * ≥ `portlash7`. 24 soatlik va 7 kunlik hisob ALOHIDA: 7 kun hali
 * o'tmagan qator 24 soatlik ulushga kiradi, 7 kunlikka kirmaydi.
 */
export function kalibrovka(
  qatorlar: KalibrQator[],
  chegaralar: { portlash24: number; portlash7: number },
): Kalibrovka {
  const b24 = qatorlar.filter((q) => q.kel24Max !== null && (q.turi === "elak" || q.turi === "namuna"));
  const b7 = qatorlar.filter((q) => q.kel7Max !== null && (q.turi === "elak" || q.turi === "namuna"));
  const p24 = (q: KalibrQator) => (q.kel24Max as number) >= chegaralar.portlash24;
  const p7 = (q: KalibrQator) => (q.kel7Max as number) >= chegaralar.portlash7;

  const guruhda = (kod: KalibrGuruhKod) => (q: KalibrQator) =>
    kod === "namuna" ? q.turi === "namuna" : q.turi === "elak" && q.nomzod === (kod === "nomzod");

  const guruhlar = {} as Record<KalibrGuruhKod, KalibrGuruh>;
  for (const kod of KALIBR_GURUHLARI) {
    const g24 = b24.filter(guruhda(kod));
    const g7 = b7.filter(guruhda(kod));
    guruhlar[kod] = {
      kun24: ulushHisobla(g24.length, g24.filter(p24).length),
      kun7: ulushHisobla(g7.length, g7.filter(p7).length),
      ortachaMax24: ortacha(g24.map((q) => q.kel24Max as number)),
      ortachaMin24: ortacha(
        g24.map((q) => q.kel24Min).filter((x): x is number => x !== null),
      ),
      kam: g24.length < KAM_NAMUNA,
    };
  }

  const holatOl = (q: KalibrQator, kod: TekshiruvKod) =>
    q.tekshiruvlar.find((t) => t.kod === kod)?.holat ?? "malumot_yoq";
  const tekshiruvlar = {} as Record<TekshiruvKod, KalibrTekshiruv>;
  for (const kod of TEKSHIRUV_KODLARI) {
    const bolim = (holat: TekshiruvHolat) => {
      const a = b24.filter((q) => holatOl(q, kod) === holat);
      const b = b7.filter((q) => holatOl(q, kod) === holat);
      return {
        kun24: ulushHisobla(a.length, a.filter(p24).length),
        kun7: ulushHisobla(b.length, b.filter(p7).length),
      };
    };
    tekshiruvlar[kod] = {
      ha: bolim("ha"),
      yoq: bolim("yoq"),
      malumotYoq: b24.filter((q) => holatOl(q, kod) === "malumot_yoq").length,
    };
  }

  const tasdiqSoni = Array.from({ length: TEKSHIRUV_KODLARI.length + 1 }, (_, soni) => {
    const a = b24.filter((q) => q.tasdiqSoni === soni);
    const b = b7.filter((q) => q.tasdiqSoni === soni);
    return {
      soni,
      kun24: ulushHisobla(a.length, a.filter(p24).length),
      kun7: ulushHisobla(b.length, b.filter(p7).length),
    };
  });

  return { jami24: b24.length, jami7: b7.length, guruhlar, tekshiruvlar, tasdiqSoni };
}

// --------------------------------------------------------------------------- //
//  Joriy natijalar bo'limlari (7-bo'lim)
// --------------------------------------------------------------------------- //

/** Oxirgi sessiyaning pooli — sahifadagi bo'limlarga.
 *
 *   tasdiqlangan — A da ham, B da ham nomzod
 *   nomzodlar    — nomzod, lekin tasdiqlanmagan
 *   otkinchi     — A da nomzod edi, B da pasaydi
 *   boshqalar    — elakdan o'tgan, qolgan hammasi
 *
 * Faqat `elak` qatorlari: `namuna` — calibration uchun, `chiqdi` —
 * jadval uchun. Tartib — sessiyadagi o'rin (yashirilganlar oxirida).
 */
export function joriyBolimlar(natijalar: Natija[]): {
  tasdiqlangan: Natija[];
  nomzodlar: Natija[];
  otkinchi: Natija[];
  boshqalar: Natija[];
} {
  const pool = natijalar
    .filter((n) => n.turi === "elak")
    .sort(
      (a, b) =>
        (a.orin ?? Infinity) - (b.orin ?? Infinity) ||
        b.tasdiqSoni - a.tasdiqSoni ||
        a.symbol.localeCompare(b.symbol),
    );
  const tasdiqlangan = pool.filter((n) => n.holat === "tasdiqlangan");
  const nomzodlar = pool.filter((n) => n.nomzod && n.holat !== "tasdiqlangan");
  const otkinchi = pool.filter((n) => n.holat === "vaqtinchalik" && !n.nomzod);
  const ishlatilgan = new Set([...tasdiqlangan, ...nomzodlar, ...otkinchi].map((n) => n.symbol));
  return {
    tasdiqlangan,
    nomzodlar,
    otkinchi,
    boshqalar: pool.filter((n) => !ishlatilgan.has(n.symbol)),
  };
}
