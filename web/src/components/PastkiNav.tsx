"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

/** Pastki navigatsiya — 5 bo'lim (mobil ilova uslubi).
 *
 * Faqat mobil qurilmalarda ko'rinadi (`lg:hidden`): desktopda yon
 * panel butun menyuni ko'rsatadi. Ikonkalar emoji emas, SVG — emoji
 * platformaga qarab har xil ko'rinadi, SVG esa hamma joyda bir xil
 * va `currentColor` orqali aktiv/nofaol rangni meros oladi.
 *
 * Har bir tab o'z ASOSIY sahifasiga (`sahifalar[0]`) olib boradi.
 * Tabning HAMMA sahifasi qulf bo'lsa, ikonka burchagida kichik qulf
 * belgisi chiqadi — va `aria-label` da ham yoziladi, shuning uchun
 * faqat rangga tayanilmaydi.
 */

const STROKE = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

/** Lucide uslubidagi SVG ikonkalar — viewBox 24×24. */
const IKONKALAR: Record<string, React.ReactNode> = {
  bosh: (
    <svg viewBox="0 0 24 24" aria-hidden {...STROKE}>
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  bozor: (
    <svg viewBox="0 0 24 24" aria-hidden {...STROKE}>
      <path d="M3 3v18h18" />
      <path d="m19 9-5 5-4-4-3 3" />
    </svg>
  ),
  akademiya: (
    <svg viewBox="0 0 24 24" aria-hidden {...STROKE}>
      <path d="M22 10 12 5 2 10l10 5z" />
      <path d="M6 12v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5" />
      <path d="M22 10v6" />
    </svg>
  ),
  produkt: (
    <svg viewBox="0 0 24 24" aria-hidden {...STROKE}>
      <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
      <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
      <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
      <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
    </svg>
  ),
  kabinet: (
    <svg viewBox="0 0 24 24" aria-hidden {...STROKE}>
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  ),
};

export type PastkiSahifa = {
  yol: string;
  nom: string;
  qulf: boolean;
  tezKunda: boolean;
};

export type PastkiTabKirish = {
  kod: string;
  nom: string;
  sahifalar: PastkiSahifa[];
};

export function PastkiNav({
  tablar,
  qulfMatn,
}: {
  tablar: PastkiTabKirish[];
  qulfMatn: string;
}) {
  const yol = usePathname();

  return (
    <nav
      aria-label="Pastki navigatsiya"
      // z-index hamburger menyusidan PAST: menyu ochilganda u butun
      // ekranni egallashi kerak, pastki nav esa uning ostida qoladi.
      className="border-ramka-yumshoq bg-fon lg:hidden fixed inset-x-0 bottom-0 z-10 border-t"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="grid grid-cols-5">
        {tablar.map((tab) => {
          if (tab.sahifalar.length === 0) return null;
          const faol = tab.sahifalar.some(
            (s) => yol === s.yol || yol.startsWith(`${s.yol}/`),
          );
          // Qulf belgisi tab QAYERGA OLIB BORSA, o'shaning holatini
          // ko'rsatsin: tugma bitta joyga (sahifalar[0]) olib boradi va
          // qulf o'sha joy haqida gapirishi kerak. Boshqa sahifalar ochiq
          // bo'lsa ham, asosiy sahifa qulflangan bo'lsa belgi chiqadi.
          const asosiyQulf = tab.sahifalar[0].qulf;
          return (
            <Link
              key={tab.kod}
              href={tab.sahifalar[0].yol}
              aria-current={faol ? "page" : undefined}
              aria-label={asosiyQulf ? `${tab.nom} — ${qulfMatn}` : undefined}
              className={cn(
                "flex flex-col items-center gap-1 py-2.5 text-[11px] leading-none transition-colors",
                faol ? "text-sarlavha" : "text-matn-past hover:text-matn",
              )}
            >
              <span
                className={cn(
                  "relative h-6 w-6 transition-opacity",
                  faol ? "opacity-100" : "opacity-60",
                )}
              >
                {IKONKALAR[tab.kod]}
                {asosiyQulf && (
                  <span
                    aria-hidden
                    className="absolute -right-1 -top-1 text-[9px] leading-none"
                  >
                    🔒
                  </span>
                )}
              </span>
              <span className={faol ? "font-semibold" : undefined}>
                {tab.nom}
              </span>
              <span
                aria-hidden
                className={cn(
                  "h-1 w-1 rounded-full transition-colors",
                  faol ? "bg-ramka" : "bg-transparent",
                )}
              />
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
