import type { SignalHolati } from "@/lib/queries";
import type { IkonkaNomi } from "@/components/ui/Ikonka";

/** Kripto narxlari juda har xil kattalikda: BTC ~60000, SHIB ~0.000008.
 *  Qat'iy 2 xona qo'ysak, arzon coinlar "0.00" bo'lib ko'rinadi. */
export function narx(n: number): string {
  const xona = n >= 1000 ? 2 : n >= 1 ? 4 : n >= 0.01 ? 6 : 8;
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: xona,
  });
}

/** PUL summasi — har doim ikki xona.
 *
 * `narx()` dan farqli: u COIN narxi uchun (arzon coinda sakkiz xona
 * kerak). Pul esa dollarda va sentdan mayda bo'lmaydi — tavsiya
 * "$426.4571" deb chiqsa, u hisoblangandek emas, tasodifiy ko'rinadi.
 */
export function pul(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function foiz(n: number | null, xona = 2): string {
  if (n === null) return "—";
  const belgi = n > 0 ? "+" : "";
  return `${belgi}${n.toFixed(xona)}%`;
}

export function sana(d: Date | null): string {
  if (!d) return "—";
  return d.toISOString().slice(0, 16).replace("T", " ");
}

/** Botdagi `_STATUS_EMOJI` bilan bir xil — har belgi BITTA ma'noda.
 *
 * TELEGRAM UCHUN qoladi: bot SVG chiza olmaydi, u faqat emoji
 * yubora oladi. Saytda esa `HOLAT_IKONKASI` ishlatiladi. */
export const HOLAT_BELGISI: Record<SignalHolati, string> = {
  pending: "⏳",
  active: "🟢",
  tp1_hit: "🎯",
  tp2_hit: "🏁",
  stopped: "🛑",
  weakening: "⚠️",
  cancelled: "⛔",
  timed_out: "⏱",
};

/** Saytdagi ko'rinish — HCS ikonka to'plamidan.
 *
 * NEGA EMOJIDAN AJRATILDI. Emoji har platformada boshqacha
 * chiziladi va rangi tizimniki: bizning ko'k-turkuaz palitramizga
 * bo'ysunmaydi. Botda esa boshqa yo'l yo'q — shuning uchun ikkita
 * jadval, ikkisi ham BIR XIL ma'noni beradi.
 *
 * `weakening` va `timed_out` uchun ogohlantirish/soat: ikkalasi ham
 * "signal yakunlanmadi, lekin nimadir noto'g'ri ketdi" degani. */
export const HOLAT_IKONKASI: Record<SignalHolati, IkonkaNomi> = {
  pending: "kutilmoqda",
  active: "faol",
  tp1_hit: "tp",
  tp2_hit: "tp",
  stopped: "stop",
  weakening: "zaiflashmoqda",
  cancelled: "bekor",
  timed_out: "kutilmoqda",
};

export const HOLAT_NOMI: Record<SignalHolati, string> = {
  pending: "Kutilmoqda",
  active: "Faol",
  tp1_hit: "TP1 olindi",
  tp2_hit: "TP2 olindi",
  stopped: "Stop",
  weakening: "Zaiflashmoqda",
  cancelled: "Bekor qilingan",
  timed_out: "Muddati tugadi",
};

export const HOLAT_NOMI_RU: Record<SignalHolati, string> = {
  pending: "Ожидание",
  active: "Активен",
  tp1_hit: "Достигнут TP1",
  tp2_hit: "Достигнут TP2",
  stopped: "Стоп",
  weakening: "Ослабевает",
  cancelled: "Отменён",
  timed_out: "Срок истёк",
};

export function holatNomi(holat: SignalHolati, til: "uz" | "ru"): string {
  return til === "ru" ? HOLAT_NOMI_RU[holat] : HOLAT_NOMI[holat];
}

/** Risk/Foyda nisbati — TP2 gacha masofa Stopgacha masofaga bo'linadi. */
export function riskFoyda(
  entry: number,
  stop: number,
  tp2: number,
): number | null {
  if (entry <= stop) return null;
  return (tp2 - entry) / (entry - stop);
}
