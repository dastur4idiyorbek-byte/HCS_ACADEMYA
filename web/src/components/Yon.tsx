"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";
import { Logo } from "@/components/ui/Logo";
import { cn } from "@/lib/cn";

/** Navigatsiya: desktopda doimiy yon panel, mobilda faqat logotip.
 *
 * Mobil navigatsiya endi pastki nav (`PastkiNav`) va bo'lim tablari
 * (`BolimTablari`) orqali ishlaydi — telefonda ikkita navigatsiya
 * bo'lmasin. Bu komponent faqat DESKTOP yon panelini chizadi; mobil
 * sarlavha esa brend ko'rsatish uchun logotip bilan qoladi.
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
    belgi: IkonkaNomi;
    qulf: boolean;
    tezKunda: boolean;
  }[];
  tarifYorliq: string | null;
  chiqishMatn: string;
  tilTanlov: React.ReactNode;
}) {
  const yol = usePathname();
  const boshSahifa = yol === "/bosh";

  const royxat = (
    <nav className="flex flex-col gap-1">
      {bandlar.map((b) => {
        const faol = yol === b.yol || yol.startsWith(`${b.yol}/`);
        return (
          <Link
            key={b.yol}
            href={b.yol}
            aria-current={faol ? "page" : undefined}
            className={cn(
              "rounded-kichik flex items-center gap-3 border px-3 py-2.5 text-sm transition",
              faol
                ? "border-ramka bg-panel-yorqin text-sarlavha font-semibold"
                : "hover:bg-panel-yorqin border-transparent",
            )}
          >
            <Ikonka nom={b.belgi} />
            <span className="flex-1">{b.nom}</span>
            {b.tezKunda && (
              <span className="text-matn-past text-[10px] uppercase">soon</span>
            )}
            {b.qulf && !b.tezKunda && (
              <Ikonka nom="qulf" className="text-matn-past h-4 w-4" />
            )}
          </Link>
        );
      })}
    </nav>
  );

  const past = (
    <div className="mt-6 space-y-3 border-t border-white/10 pt-4">
      {tarifYorliq && (
        <p className="text-matn-past text-xs">
          <span className="text-sarlavha font-semibold">{tarifYorliq}</span>
        </p>
      )}
      {tilTanlov}
      <form action="/api/auth/chiqish" method="post">
        <button
          type="submit"
          className="text-matn-past hover:text-sarlavha inline-block py-0 text-xs underline underline-offset-4"
        >
          {chiqishMatn}
        </button>
      </form>
    </div>
  );

  return (
    <>
      {/* Mobil sarlavha — faqat logotip, navigatsiya pastki navda. */}
      {/* Mobil sarlavha — FAQAT logotip.
          Bosh sahifada CHIQMAYDI: u yerda o'zining logotipli
          yopishgan qatori bor (`BoshTepasi`) va ikkalasi ustma-ust
          tushib, telefon ekranining uchdan birini ikkita bir xil
          logotip egallab olardi. */}
      {!boshSahifa && (
        <header className="border-ramka-yumshoq bg-fon sticky top-0 z-30 flex h-14 items-center border-b px-4 lg:hidden">
          <Logo size={32} />
        </header>
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
