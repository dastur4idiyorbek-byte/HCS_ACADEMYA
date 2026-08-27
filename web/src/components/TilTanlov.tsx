"use client";

import { usePathname } from "next/navigation";

import { TIL_NOMLARI, type Til } from "@/lib/i18n";
import { cn } from "@/lib/cn";

/** Til almashtirish — forma orqali (server cookie yozadi).
 *
 * Nima uchun `fetch` emas: cookie serverda o'rnatilishi va sahifa qaytadan
 * server tomonda render bo'lishi kerak. Oddiy forma buni JS'siz ham
 * bajaradi.
 */
export function TilTanlov({ joriy }: { joriy: Til }) {
  const yol = usePathname();
  return (
    <form action="/api/til" method="post" className="flex gap-1">
      <input type="hidden" name="qayerga" value={yol} />
      {(Object.keys(TIL_NOMLARI) as Til[]).map((til) => (
        <button
          key={til}
          type="submit"
          name="til"
          value={til}
          aria-pressed={til === joriy}
          className={cn(
            "rounded-kichik border px-2.5 py-1 text-xs transition",
            til === joriy
              ? "border-ramka text-sarlavha font-semibold"
              : "text-matn-past hover:text-sarlavha border-transparent",
          )}
        >
          {til.toUpperCase()}
        </button>
      ))}
    </form>
  );
}
