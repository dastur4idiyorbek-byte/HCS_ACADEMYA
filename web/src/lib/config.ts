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
