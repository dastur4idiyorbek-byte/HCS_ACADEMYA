import type { SignalHolati } from "@/lib/queries";

/** Kripto narxlari juda har xil kattalikda: BTC ~60000, SHIB ~0.000008.
 *  Qat'iy 2 xona qo'ysak, arzon coinlar "0.00" bo'lib ko'rinadi. */
export function narx(n: number): string {
  const xona = n >= 1000 ? 2 : n >= 1 ? 4 : n >= 0.01 ? 6 : 8;
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: xona });
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

/** Botdagi `_STATUS_EMOJI` bilan bir xil — har belgi BITTA ma'noda. */
export const HOLAT_BELGISI: Record<SignalHolati, string> = {
  pending: "⏳",
  active: "🟢",
  tp1_hit: "🎯",
  tp2_hit: "🏁",
  stopped: "🛑",
  weakening: "⚠️",
  cancelled: "⛔",
};

export const HOLAT_NOMI: Record<SignalHolati, string> = {
  pending: "Kutilmoqda",
  active: "Faol",
  tp1_hit: "TP1 olindi",
  tp2_hit: "TP2 olindi",
  stopped: "Stop",
  weakening: "Zaiflashmoqda",
  cancelled: "Bekor qilingan",
};

export const HOLAT_NOMI_RU: Record<SignalHolati, string> = {
  pending: "Ожидание",
  active: "Активен",
  tp1_hit: "Достигнут TP1",
  tp2_hit: "Достигнут TP2",
  stopped: "Стоп",
  weakening: "Ослабевает",
  cancelled: "Отменён",
};

export function holatNomi(holat: SignalHolati, til: "uz" | "ru"): string {
  return til === "ru" ? HOLAT_NOMI_RU[holat] : HOLAT_NOMI[holat];
}

/** Risk/Foyda nisbati — TP2 gacha masofa Stopgacha masofaga bo'linadi. */
export function riskFoyda(entry: number, stop: number, tp2: number): number | null {
  if (entry <= stop) return null;
  return (tp2 - entry) / (entry - stop);
}
