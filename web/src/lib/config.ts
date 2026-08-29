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

/** Bozor Salomatligi bandlari — shkaladagi zonalarni belgilaydi.
 *
 * DIQQAT: bu qiymatlar `scoring.thresholds` ostida, `market_health`
 * ostida EMAS. Yo'l noto'g'ri bo'lsa `yol()` jimgina zaxira qiymatni
 * qaytaradi — ya'ni xato ko'rinmaydi. Aynan shuning uchun
 * `tests/config.test.ts` yo'llarni tekshiradi. */
export function salomatlikBandlari(): { high: number; mid: number } {
  return {
    high: yol(["scoring", "thresholds", "health_high_min"], 65),
    mid: yol(["scoring", "thresholds", "health_mid_min"], 40),
  };
}

/** Savdo qoidalari — qo'lda kiritilgan signalni TEKSHIRISH uchun.
 *
 * Bu qiymatlar botdagi `_rule_warnings` bilan bir xil manbadan
 * (`config/default.yaml`) o'qiladi. Nusxa ko'chirilsa, sayt bir chegara,
 * bot esa boshqasi bo'yicha ogohlantirardi va admin qaysi biriga
 * ishonishni bilmasdi.
 *
 * DIQQAT: bular TAQIQ emas, OGOHLANTIRISH. Botda ham shunday — admin
 * bilib turib qoidadan chetga chiqadigan signal berishi mumkin
 * (3.3-band qo'lda signalda majburiy emas).
 */
export function savdoQoidalari(): {
  maxStopPct: number;
  minTpPct: number;
  maxTpPct: number;
  minRiskReward: number;
} {
  return {
    maxStopPct: yol(["trade_rules", "max_stop_distance_pct"], 8),
    minTpPct: yol(["trade_rules", "min_tp_distance_pct"], 3),
    maxTpPct: yol(["trade_rules", "max_tp_distance_pct"], 20),
    minRiskReward: yol(["trade_rules", "min_risk_reward"], 3),
  };
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
  return yol(["portfolio", "tp1_close_pct"], 50);
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

/** CryptoSpot3% (SMC/LIT/ICT) sozlamalari — admin panelida KO'RSATISH uchun.
 *
 * FAQAT O'QISH. Bu loyihada barcha strategiya parametrlari
 * `config/default.yaml` da yashaydi va joylashtirishda o'zgaradi;
 * ishga tushgan tizimda ularni tahrirlaydigan mexanizm yo'q. Panelda
 * "tahrirlash" tugmasini ko'rsatib, aslida hech narsa saqlamaslik —
 * eng yomon variant: admin o'zgartirdim deb o'ylaydi, tizim esa eski
 * qiymat bilan ishlaydi.
 *
 * Shuning uchun panel amaldagi qiymatni ko'rsatadi va ular qayerdan
 * kelishini ochiq aytadi.
 */
export function smcSozlamalari(): {
  strukturaMajburiy: boolean;
  yalashYoqilgan: boolean;
  yalashChuqurligi: number;
  yalashOynasi: number;
  qaytishShamlari: number;
  sessiyaYoqilgan: boolean;
  sessiyaBoshi: number;
  sessiyaOxiri: number;
  bonusStruktura: number;
  bonusYalash: number;
  bonusSessiya: number;
} {
  return {
    strukturaMajburiy: yol(["analysis", "require_structure_alignment"], false),
    yalashYoqilgan: yol(["analysis", "liquidity_sweep", "enabled"], true),
    yalashChuqurligi: yol(["analysis", "liquidity_sweep", "min_sweep_pct"], 0.3),
    yalashOynasi: yol(["analysis", "liquidity_sweep", "lookback_bars"], 30),
    qaytishShamlari: yol(["analysis", "liquidity_sweep", "max_reclaim_bars"], 3),
    sessiyaYoqilgan: yol(["analysis", "session_overlap", "enabled"], true),
    sessiyaBoshi: yol(["analysis", "session_overlap", "start_hour_utc"], 13),
    sessiyaOxiri: yol(["analysis", "session_overlap", "end_hour_utc"], 16),
    bonusStruktura: yol(["scoring", "bonuses", "structure"], 10),
    bonusYalash: yol(["scoring", "bonuses", "liquidity_sweep"], 10),
    bonusSessiya: yol(["scoring", "bonuses", "session_overlap"], 5),
  };
}
