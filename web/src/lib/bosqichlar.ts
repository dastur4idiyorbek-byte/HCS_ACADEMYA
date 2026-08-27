import { readFileSync } from "node:fs";
import path from "node:path";

/** Rad etish bosqichlarining nomlari — MANBA `core/pipeline/context.py`.
 *
 * Nima uchun nusxa ko'chirmaymiz: bu loyihada bir necha marta takrorlangan
 * xato bor — "bitta qiymat ikki joyda yozilgan, biri o'zgargan, ikkinchisi
 * qolib ketgan" (docs/ARXITEKTURA.md dagi 1- va 4-naqshlar). Bosqichlar
 * ro'yxati esa o'sib boradi: yangi strategiya qo'shilsa yangi bosqich
 * paydo bo'ladi. Nusxa saqlasak, saytda `classic_ta:zone_position` kabi
 * xom kod ko'rinib qolardi.
 *
 * Python fayli oddiy `dict[str, str]` literalidan iborat — uni o'qish
 * xavfsiz. O'qib bo'lmasa, bosqich kodining O'ZI ko'rsatiladi (Python
 * tomondagi `stage_label()` ham aynan shunday qiladi).
 *
 * TARTIB SAQLANADI: Python'dagi dict tartibi — quvurdagi (pipeline)
 * bosqichlar ketma-ketligi. Voronka aynan shu tartibda chiziladi.
 */

type Bosqichlar = { nomlar: Map<string, string>; vaqtDarvozalari: Set<string> };

let kesh: Bosqichlar | null = null;

function pythonYoli(): string {
  return (
    process.env.HCS_PIPELINE_CONTEXT?.trim() ||
    path.resolve(process.cwd(), "..", "core", "pipeline", "context.py")
  );
}

/** `{` dan boshlab MOS KELUVCHI `}` gacha bo'lgan qismni qaytaradi.
 *
 * Nima uchun qavslarni sanaymiz: `ROUTINE_STAGES` ichma-ich yozilgan
 * (`frozenset(\n    {\n ... }\n)`), ya'ni yopuvchi qavs qatorning
 * boshida turmaydi. "Birinchi \n} ni top" degan sodda qoida uni
 * jimgina o'tkazib yuborardi. */
function blokniAjrat(manba: string, nom: string): string | null {
  const boshi = manba.indexOf(nom);
  if (boshi === -1) return null;
  const ochilish = manba.indexOf("{", boshi);
  if (ochilish === -1) return null;

  let chuqurlik = 0;
  for (let i = ochilish; i < manba.length; i += 1) {
    if (manba[i] === "{") chuqurlik += 1;
    else if (manba[i] === "}") {
      chuqurlik -= 1;
      if (chuqurlik === 0) return manba.slice(ochilish + 1, i);
    }
  }
  return null;
}

function oqi(): Bosqichlar {
  if (kesh) return kesh;
  const nomlar = new Map<string, string>();
  const vaqtDarvozalari = new Set<string>();

  try {
    // turbopackIgnore: bu fayl loyiha ildizida, `web/` dan tashqarida.
    // Sayt bot BILAN BIR SERVERDA ishlaydi (Railway'dagi bitta xizmat),
    // shuning uchun `core/` doim yonida bo'ladi. Turbopack esa buni
    // "butun loyihani nusxalab yuborish" deb ogohlantiradi — bizda esa
    // loyiha allaqachon o'sha yerda.
    const manba = readFileSync(/* turbopackIgnore: true */ pythonYoli(), "utf8");

    const nomBloki = blokniAjrat(manba, "STAGE_LABELS: dict[str, str] =");
    if (nomBloki) {
      // "kalit": "qiymat",  — qiymat ichida qo'shtirnoq yo'q
      for (const m of nomBloki.matchAll(/"([^"]+)"\s*:\s*"([^"]*)"/g)) {
        nomlar.set(m[1], m[2]);
      }
    }

    const darvozaBloki = blokniAjrat(manba, "ROUTINE_STAGES: frozenset[str] =");
    if (darvozaBloki) {
      for (const m of darvozaBloki.matchAll(/"([^"]+)"/g)) vaqtDarvozalari.add(m[1]);
    }
  } catch {
    // Fayl topilmadi (masalan sayt alohida joylashtirilgan) — bosqich
    // kodlari xom ko'rinadi, lekin sahifa ishlayveradi.
  }

  kesh = { nomlar, vaqtDarvozalari };
  return kesh;
}

export function bosqichNomi(kod: string): string {
  return oqi().nomlar.get(kod) ?? kod;
}

/** Vaqt darvozasi — TASHXIS EMAS, soat ko'rsatkichi.
 *
 * Skalping oynasi kuniga atigi 45 daqiqa ochiq, ya'ni qolgan vaqtda
 * "oyna yopiq" yozuvi har siklda, har coin uchun yoziladi. Foizga
 * qo'shilsa, u haqiqiy sabablarni pastga surib yuboradi. */
export function vaqtDarvozasimi(kod: string): boolean {
  return oqi().vaqtDarvozalari.has(kod);
}

/** Python dict'dagi joylashuv — bir guruh ichida tartib beradi. */
export function bosqichTartibi(kod: string): number {
  const kalitlar = [...oqi().nomlar.keys()];
  const indeks = kalitlar.indexOf(kod);
  return indeks === -1 ? kalitlar.length : indeks;
}

/** Voronkadagi tartib — nomzod QAYSI KETMA-KETLIKDA tekshiriladi.
 *
 * Python'dagi `STAGE_LABELS` guruhlab yozilgan (avval sikl darajasi,
 * keyin strategiyalar) — bu o'qish uchun qulay, lekin voronka uchun
 * TESKARI: unda "ball chegarasi" birinchi bo'lib chiqib qolardi,
 * holbuki nomzod avval strategiya filtrlaridan o'tadi va ballga
 * keyin yetib boradi.
 *
 * Shuning uchun tartib ro'yxat ko'chirib olinmaydi, balki bosqich
 * kodining PREFIKSIDAN chiqariladi:
 *   1. strategiya filtrlari  (`classic_ta:`, `opening_range_scalp:`)
 *   2. ball chegarasi        (`threshold`)
 *   3. yakuniy darvozalar    (`risk_engine:`, `market_health`)
 *
 * Yangi strategiya qo'shilsa, u avtomatik 1-guruhga tushadi.
 */
export function voronkaTartibi(kod: string): number {
  const guruh =
    kod.startsWith("risk_engine") || kod === "market_health" ? 2 : kod === "threshold" ? 1 : 0;
  return guruh * 1000 + bosqichTartibi(kod);
}

export function nechtaBosqichNomiBor(): number {
  return oqi().nomlar.size;
}
