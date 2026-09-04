"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/ui/Logo";
import { cn } from "@/lib/cn";

/** Navigatsiya: desktopda doimiy yon panel, mobilda hamburger.
 *
 * Bitta komponent, ikki ko'rinish — ro'yxat bir joyda tursin. Ikkita
 * alohida komponent bo'lsa, yangi bo'lim qo'shilganda biri unutiladi.
 */
export function Yon({
  bandlar,
  tarifYorliq,
  chiqishMatn,
  tilTanlov,
}: {
  bandlar: {
    yol: string;
    nom: string;
    belgi: string;
    qulf: boolean;
    tezKunda: boolean;
  }[];
  tarifYorliq: string | null;
  chiqishMatn: string;
  tilTanlov: React.ReactNode;
}) {
  const yol = usePathname();
  const [ochiq, setOchiq] = useState(false);

  // O'LCHAMLAR MOBILDA KATTAROQ. Ro'yxat ikkala ko'rinishda ham bitta,
  // shuning uchun o'lchov `lg:` bilan ajratiladi: telefonda barmoq uchun
  // yetarli (band balandligi ~52px, tavsiya etilgan eng kam 44px),
  // desktopda esa tor yon panelga sig'adigan ixcham holicha qoladi.
  const royxat = (
    <nav className="flex flex-col gap-1.5 lg:gap-1">
      {bandlar.map((b) => {
        const faol = yol === b.yol || yol.startsWith(`${b.yol}/`);
        return (
          <Link
            key={b.yol}
            href={b.yol}
            // Mobilda menyu ochiq qolsa, foydalanuvchi bosgan sahifasini
            // ko'rmaydi va "bosilmadi" deb o'ylaydi. Effekt o'rniga aynan
            // bosish hodisasida yopamiz — sabab va natija bir joyda turadi.
            onClick={() => setOchiq(false)}
            aria-current={faol ? "page" : undefined}
            className={cn(
              "rounded-kichik flex items-center gap-3.5 border px-4 py-3.5 text-base transition",
              "lg:gap-3 lg:px-3 lg:py-2.5 lg:text-sm",
              faol
                ? "border-ramka bg-panel-yorqin text-sarlavha font-semibold"
                : "hover:bg-panel-yorqin border-transparent",
            )}
          >
            <span
              aria-hidden
              className="w-6 text-center text-lg lg:w-5 lg:text-base"
            >
              {b.belgi}
            </span>
            <span className="flex-1">{b.nom}</span>
            {b.tezKunda && (
              <span className="text-matn-past text-[11px] uppercase lg:text-[10px]">
                soon
              </span>
            )}
            {b.qulf && !b.tezKunda && <span aria-hidden>🔒</span>}
          </Link>
        );
      })}
    </nav>
  );

  const past = (
    <div className="mt-6 space-y-4 border-t border-white/10 pt-5 lg:mt-6 lg:space-y-3 lg:pt-4">
      {tarifYorliq && (
        <p className="text-matn-past text-sm lg:text-xs">
          <span className="text-sarlavha font-semibold">{tarifYorliq}</span>
        </p>
      )}
      {tilTanlov}
      <form action="/api/auth/chiqish" method="post">
        <button
          type="submit"
          className="text-matn-past hover:text-sarlavha inline-block py-1 text-sm underline underline-offset-4 lg:py-0 lg:text-xs"
        >
          {chiqishMatn}
        </button>
      </form>
    </div>
  );

  return (
    <>
      {/* Mobil sarlavha */}
      <header className="border-ramka-yumshoq bg-fon sticky top-0 z-30 flex items-center justify-between border-b px-4 py-3 lg:hidden">
        <Logo size={32} />
        <button
          type="button"
          onClick={() => setOchiq((x) => !x)}
          aria-expanded={ochiq}
          aria-label="Menyu"
          className="border-ramka rounded-kichik border px-4 py-2.5 text-xl leading-none"
        >
          {ochiq ? "✕" : "☰"}
        </button>
      </header>

      {ochiq && (
        <div className="border-ramka-yumshoq bg-fon fixed inset-x-0 top-[57px] bottom-0 z-20 overflow-y-auto border-b px-4 py-4 lg:hidden">
          {royxat}
          {past}
        </div>
      )}

      {/* Desktop yon panel */}
      <aside className="border-ramka-yumshoq hidden w-64 shrink-0 border-r p-5 lg:sticky lg:top-0 lg:block lg:h-dvh lg:overflow-y-auto">
        <div className="mb-6">
          <Logo />
        </div>
        {royxat}
        {past}
      </aside>
    </>
  );
}
