"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";

/** Admin bo'limlari orasida o'tish. Gorizontal, chunki ular ko'p emas
 *  va yon panel allaqachon band. */
export function AdminYonMenyu({
  bandlar,
  sarlavha,
}: {
  bandlar: { yol: string; nom: string; belgi: IkonkaNomi }[];
  sarlavha: string;
}) {
  const yol = usePathname();
  return (
    <nav aria-label={sarlavha} className="mb-5 flex flex-wrap gap-2">
      {bandlar.map((b) => {
        const faol = yol === b.yol;
        return (
          <Link
            key={b.yol}
            href={b.yol}
            aria-current={faol ? "page" : undefined}
            className={cn(
              "rounded-tugma flex items-center gap-2 border px-3 py-2 text-sm transition",
              faol
                ? "border-ramka bg-panel-yorqin text-sarlavha font-semibold"
                : "border-ramka-yumshoq hover:bg-panel-yorqin",
            )}
          >
            <Ikonka nom={b.belgi} className="h-4 w-4" />
            {b.nom}
          </Link>
        );
      })}
    </nav>
  );
}
