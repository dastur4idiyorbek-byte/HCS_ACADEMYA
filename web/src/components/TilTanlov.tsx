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
    <form action="/api/til" method="post" className="flex gap-2 lg:gap-1">
      <input type="hidden" name="qayerga" value={yol} />
      {(Object.keys(TIL_NOMLARI) as Til[]).map((til) => (
        <button
          key={til}
          type="submit"
          name="til"
          value={til}
          aria-pressed={til === joriy}
          className={cn(
            // Mobilda barmoq uchun kattaroq, desktopda ixcham holicha —
            // yon panel tor va u yerda sichqoncha ishlatiladi.
            "rounded-kichik border px-4 py-2 text-sm transition",
            "lg:px-2.5 lg:py-1 lg:text-xs",
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
