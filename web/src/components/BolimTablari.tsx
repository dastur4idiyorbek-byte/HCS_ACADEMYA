"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

type Sahifa = {
  yol: string;
  nom: string;
  qulf: boolean;
  tezKunda: boolean;
};

type Tab = {
  kod: string;
  nom: string;
  sahifalar: Sahifa[];
};

/** Bo'lim ichidagi kichik tab qatori — faqat mobil.
 *
 * Pastki nav 5 ta katta bo'limni ko'rsatadi, lekin ayrim bo'limlar
 * bir necha sahifadan iborat (Bozor = Salomatlik + Ko'rinish,
 * Kabinet = Profil + Portfel + Admin). Bu komponent joriy yo'l qaysi
 * tabga tegishli ekanini topib, O'SHA tabning sahifalarini sahifa
 * tepasida gorizontal qator qilib chiqaradi.
 *
 * Sahifa bitta bo'lsa — hech narsa ko'rsatilmaydi: bitta sahifaga
 * bitta havola qo'yish shovqin bo'lardi.
 */
export function BolimTablari({ tablar }: { tablar: Tab[] }) {
  const yol = usePathname();

  const faolTab = tablar.find((tab) =>
    tab.sahifalar.some((s) => yol === s.yol || yol.startsWith(`${s.yol}/`)),
  );

  if (!faolTab || faolTab.sahifalar.length <= 1) return null;

  return (
    <nav
      aria-label="Bo'lim sahifalari"
      // `overflow-x-auto` FAQAT shu qatorda: ko'p sahifa tor ekranga
      // sig'masa gorizontal siljiydi, sahifaning O'ZI surilmaydi.
      className="mb-4 max-w-full overflow-x-auto lg:hidden"
    >
      <div className="flex gap-1 border-b border-white/10 whitespace-nowrap">
        {faolTab.sahifalar.map((s) => {
          const faol = yol === s.yol || yol.startsWith(`${s.yol}/`);
          return (
            <Link
              key={s.yol}
              href={s.yol}
              aria-current={faol ? "page" : undefined}
              className={cn(
                "-mb-px border-b-2 px-3 py-2 text-sm transition-colors",
                faol
                  ? "border-sarlavha text-sarlavha font-semibold"
                  : "border-transparent text-matn-past hover:text-matn",
              )}
            >
              {s.nom}
              {s.qulf && <span aria-hidden> 🔒</span>}
              {s.tezKunda && (
                <span className="text-matn-past ml-1 text-[10px] uppercase">
                  soon
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
