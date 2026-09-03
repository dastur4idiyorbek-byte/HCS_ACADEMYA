import { readFileSync } from "node:fs";
import path from "node:path";

import { parse } from "yaml";

/** Bot konfiguratsiyasini o'qish — `config/default.yaml`.
 *
 * Nima uchun qiymatlarni bu yerga ko'chirib yozmaymiz: obuna muddati
 * (kunlik 1 kun, oylik 30 kun) botda YAML dan olinadi. Agar sayt o'z
 * nusxasini saqlasa, bir kuni kimdir YAML ni o'zgartiradi va sayt eski
 * qiymat bilan obuna ochib qo'yadi — ikkalasi bir xil to'lov uchun turli
 * muddat beradi. Bu — loyihaning 6.4-bandidagi "sehrli raqam yo'q"
 * qoidasining aynan o'zi.
 */

type Yaml = Record<string, unknown>;

let kesh: Yaml | null = null;

function yamlni_oqi(): Yaml {
  if (kesh) return kesh;
  // Sayt `web/` ichida ishlaydi, konfiguratsiya esa loyiha ILDIZIDA.
  //
  // `HCS_CONFIG_FILE` bot bilan umumiy o'zgaruvchi va u odatda NISBIY
  // yoziladi (`config/default.yaml`). Bot ildizdan ishga tushadi, sayt
  // esa `web/` dan — ya'ni o'sha nisbiy yo'l ikkalasi uchun BOSHQA-BOSHQA
  // faylni bildiradi. Shuning uchun nisbiy yo'l doim ildizga nisbatan
  // hisoblanadi, `process.cwd()` ga emas.
  const ildiz = path.resolve(process.cwd(), "..");
  const berilgan = process.env.HCS_CONFIG_FILE?.trim();
  const yol = berilgan
    ? path.resolve(ildiz, berilgan)
    : path.join(ildiz, "config", "default.yaml");
  kesh = parse(readFileSync(/* turbopackIgnore: true */ yol, "utf8")) as Yaml;
  return kesh;
}

function yol<T>(kalitlar: string[], zaxira: T): T {
  let joriy: unknown = yamlni_oqi();
  for (const k of kalitlar) {
    if (typeof joriy !== "object" || joriy === null) return zaxira;
    joriy = (joriy as Yaml)[k];
  }
  return (joriy as T) ?? zaxira;
}

/** YAML dagi ixtiyoriy yo'lni o'qish — takrorlanadigan o'ramsiz.
 *
 * `yol()` xususiy edi va har bir qiymat uchun alohida funksiya
 * yozilardi. Pozitsiya hajmi hisobiga oltita parametr kerak, ular
 * uchun oltita o'ram yozish — shovqin.
 */
export function sozlama<T>(kalitlar: string[], zaxira: T): T {
  return yol(kalitlar, zaxira);
}

/** Obuna muddati kunlarda. Zaxira qiymatlar — YAML o'qilmay qolgan holat
 *  uchun; ular botning standart qiymatlari bilan bir xil. */
export function obunaKunlari(): { daily: number; monthly: number } {
  return {
    daily: yol(["subscriptions", "periods", "daily"], 1),
    monthly: yol(["subscriptions", "periods", "monthly"], 30),
  };
}

/** Savdo qoidalari — qo'lda kiritilgan signalni TEKSHIRISH uchun.
 *
 * 2026-09-03 — ilgari bu qiymatlar `config/default.yaml` dagi
 * `trade_rules` blokidan o'qilardi. Eski tahlil moduli olib
 * tashlanganda o'sha blok ham ketdi: uning qolgan qismi (nisbat poli,
 * TP2 tuzilmadan, oraliqlar) faqat avtomatik siklga tegishli edi.
 *
 * Endi to'rtta raqam SHU YERDA, ochiq turadi. YAML dan o'qishni
 * saqlash yomonroq bo'lardi: `yol()` bloki yo'q kalitni jimgina
 * zaxira qiymatga almashtiradi, ya'ni sayt "YAML dan o'qidim" deb
 * turib, aslida shu yerdagi raqamni ko'rsatardi.
 *
 * DIQQAT: bular TAQIQ emas, OGOHLANTIRISH. Admin bilib turib
 * qoidadan chetga chiqadigan signal berishi mumkin.
 */
export function savdoQoidalari(): {
  maxStopPct: number;
  minTpPct: number;
  maxTpPct: number;
  minRiskReward: number;
} {
  return { maxStopPct: 8, minTpPct: 3, maxTpPct: 20, minRiskReward: 3 };
}

/** Spot juftlik kotirovkasi — `DOT` dan `DOTUSDT` yasash uchun.
 *
 * Bot ham shu qiymatni ishlatadi (`core/halal_screening/screener.py` ->
 * `pair_for()`). Bu yerga ko'chirib yozilsa, YAML o'zgargan kuni sayt
 * grafikni mavjud bo'lmagan juftlikda so'rardi va TradingView "This
 * symbol doesn't exist" deb turardi — bu allaqachon bir marta bo'ldi,
 * faqat boshqa sababdan.
 */
export function kotirovka(): string {
  return yol(["halal_screening", "quote_asset"], "USDT");
}

/** TP1 da pozitsiyaning qancha qismi sotiladi (foizda).
 *
 * Bot signal kartochkasida aynan shu qiymatni yozadi
 * (`bot/formatting.py` -> `render_levels`). Sayt uni ko'chirib
 * yozsa, ikkalasi bir xil signal uchun boshqa-boshqa ulush
 * ko'rsatardi va foydalanuvchi qaysi biriga ishonishni bilmasdi.
 */
export function tp1Ulushi(): number {
  return tpUlushlari(2)[0];
}

/** `count` ta TP uchun ulushlar jadvali.
 *
 * TP soni qat'iy emas — 1, 2 yoki 3 bo'lishi mumkin. Ulushlar
 * botdagi `portfolio.tp_close_shares` bilan BIR XIL manbadan
 * o'qiladi: ilgari sayt "TP2 = 100 dan qolgani" deb o'zi
 * hisoblardi va uchinchi TP unga sig'masdi.
 */
export function tpUlushlari(count: number): number[] {
  const jadval = yol(["portfolio", "tp_close_shares"], null) as
    | number[][]
    | null;
  const qator = jadval?.[count - 1];
  if (Array.isArray(qator) && qator.length === count) {
    return qator.map(Number);
  }
  return Array.from({ length: count }, () => 100 / count);
}

/** Eng kichik pozitsiya hajmi (USD).
 *
 * Botdagi `save_position` ham aynan shu chegarani qo'llaydi
 * (`bot/handlers/portfolio.py`). Ikki joyda ikki xil bo'lsa,
 * botda rad etilgan miqdor saytda o'tib ketardi.
 */
export function engKichikPozitsiya(): number {
  return yol(["portfolio", "min_position_usd"], 1);
}

/** Sinov davri — Bozor Salomatligidan chiqarilgan omillar (59-bo'lim).
 *
 * Saytga KO'CHIRIB YOZILMAYDI: sana va omillar ro'yxati YAML da, ya'ni
 * bot bilan bitta manbada. Aks holda muddat tugagach bot omilni qaytarib
 * hisoblardi, sayt esa hali ham "hisobga olinmadi" deb turardi.
 */
export function sinovDavri(): {
  yoqilgan: boolean;
  boshlanish: string;
  kunlar: number;
  /** Indeksdan chiqarilgan omillar */
  chiqarilgan: string[];
  /** Vaqtincha to'xtatilgan Risk Engine qoidalari */
  toxtatilgan: string[];
} {
  return {
    yoqilgan: sozlama(["sinov", "enabled"], true),
    boshlanish: String(sozlama(["sinov", "start_date"], "2026-08-29")),
    kunlar: sozlama(["sinov", "days"], 100),
    chiqarilgan: sozlama(
      ["sinov", "exclude_health_factors"],
      ["aggregate_user_capacity"] as string[],
    ),
    toxtatilgan: sozlama(["sinov", "suspend_risk_rules"], [] as string[]),
  };
}

/** Shu lahzada sinov davri kuchdami va necha kun qoldi.
 *
 * `paytida` — indeks HISOBLANGAN vaqt, "hozir" emas: ekrandagi shkala
 * o'sha lahzaning surati, ikkalasi bir vaqtga tegishli bo'lishi kerak.
 */
export function sinovHolati(paytida: Date): {
  faol: boolean;
  qolganKun: number;
  chiqarilgan: string[];
  toxtatilgan: string[];
} {
  const s = sinovDavri();
  const bosh = new Date(`${s.boshlanish}T00:00:00Z`);
  const tugash = new Date(bosh.getTime() + s.kunlar * 86_400_000);
  const kun = new Date(
    Date.UTC(paytida.getUTCFullYear(), paytida.getUTCMonth(), paytida.getUTCDate()),
  );
  const faol = s.yoqilgan && kun >= bosh && kun < tugash;
  return {
    faol,
    qolganKun: Math.max(0, Math.round((tugash.getTime() - kun.getTime()) / 86_400_000)),
    chiqarilgan: s.chiqarilgan,
    toxtatilgan: s.toxtatilgan,
  };
}

/** Kech kirish ogohlantirishi chegarasi (foiz).
 *
 * Bot bilan BITTA manba: `trade_rules.late_entry_warn_pct`. Saytga
 * ko'chirib yozilsa, admin YAML'ni o'zgartirganda sayt eski chegarada
 * qolib ketardi. */
export function kechKirishChegarasi(): number {
  // Ilgari `trade_rules.late_entry_warn_pct` dan o'qilardi. O'sha blok
  // eski tahlil moduli bilan ketdi — `savdoQoidalari()` izohiga qarang.
  return 1.2;
}
