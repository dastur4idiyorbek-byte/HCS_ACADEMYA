"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";

/** Pastki navigatsiya — mobil ilova uslubidagi asosiy tugmalar.
 *
 * Faqat mobil qurilmalarda ko'rinadi (`lg:hidden`): desktopda yon
 * panel butun menyuni ko'rsatadi. Ikonkalar HCS to'plamidan
 * (`ui/Ikonka.tsx`) — emoji platformaga qarab har xil ko'rinadi,
 * SVG esa hamma joyda bir xil va `currentColor` orqali aktiv/nofaol
 * rangni meros oladi.
 *
 * Har bir tab o'z ASOSIY sahifasiga (`sahifalar[0]`) olib boradi.
 * Tabning HAMMA sahifasi qulf bo'lsa, ikonka burchagida kichik qulf
 * belgisi chiqadi — va `aria-label` da ham yoziladi, shuning uchun
 * faqat rangga tayanilmaydi.
 */

/** Tab kodi -> HCS ikonka tizimidagi nom.
 *
 * Ilgari bu yerda ikonkalar O'Z QO'LIDA chizilgan edi. Endi ular
 * `ui/Ikonka.tsx` da, butun sayt bilan bitta to'plamda: pastki
 * navdagi "Akademiya" bilan yon paneldagi "Akademiya" bir xil
 * ko'rinishi kerak, ikki joyda ikki xil chizilsa esa ular asta
 * ajralib ketardi.
 */
const TAB_IKONKASI: Record<string, IkonkaNomi> = {
  bosh: "bosh",
  bozor: "bozor_holati",
  akademiya: "akademiya",
  produkt: "produkt",
  modul: "korish",
  kabinet: "kabinet",
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
  // Sahifasi qolmagan tab UMUMAN chizilmaydi — panjarada ham joy
  // egallamaydi.
  const korinadigan = tablar.filter((t) => t.sahifalar.length > 0);
  if (korinadigan.length === 0) return null;

  return (
    <nav
      aria-label="Pastki navigatsiya"
      // z-index hamburger menyusidan PAST: menyu ochilganda u butun
      // ekranni egallashi kerak, pastki nav esa uning ostida qoladi.
      className="border-ramka-yumshoq bg-fon lg:hidden fixed inset-x-0 bottom-0 z-10 border-t"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      {/* USTUN SONI RO'YXATDAN OLINADI, qo'lda yozilmaydi.
          Ilgari ustun soni Tailwind sinfida QATTIQ yozilgan edi va
          tab soni o'zgarganda panjara ajralib ketardi. Bundan tashqari
          bo'sh tab (hamma sahifasi adminga xos) panjarada JOY
          egallab turardi: 5 ustun, 4 tugma va bitta teshik. */}
      <div
        className="grid"
        style={{ gridTemplateColumns: `repeat(${korinadigan.length}, minmax(0, 1fr))` }}
      >
        {korinadigan.map((tab) => {
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
                <Ikonka
                  nom={TAB_IKONKASI[tab.kod] ?? "produkt"}
                  className="h-6 w-6"
                />
                {asosiyQulf && (
                  <Ikonka
                    nom="qulf"
                    className="bg-fon absolute -top-1 -right-1 h-3 w-3 rounded-full"
                  />
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
