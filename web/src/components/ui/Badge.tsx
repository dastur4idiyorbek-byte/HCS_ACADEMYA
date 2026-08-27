import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type BadgeTone = "yaxshi" | "ortacha" | "past" | "neytral";

const TONLAR: Record<BadgeTone, string> = {
  yaxshi: "border-yaxshi/60 text-yaxshi",
  ortacha: "border-ortacha/60 text-ortacha",
  past: "border-past/70 text-past",
  neytral: "border-matn-past/50 text-matn-past",
};

/** Holat yorlig'i — signal holati, obuna tarifi va h.k.
 *
 * Fon — sahifaning to'q ko'ki (kartochkadan bir pog'ona to'qroq), ramka va
 * matn esa holat rangida. Nima uchun to'qroq fon kerak: yorliq matni kichik,
 * kartochka fonida qizil 3.8:1 beradi — WCAG AA talabidan past. Bir pog'ona
 * to'q fonda esa 5.0:1 bo'ladi. Buni `python3 scripts/kontrast.py` tekshiradi.
 */
export function Badge({
  children,
  tone = "neytral",
  className,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "bg-fon inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        TONLAR[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
