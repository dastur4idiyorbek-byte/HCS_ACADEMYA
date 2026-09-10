"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";

/** Bosh sahifaning YOPISHIB turadigan tepasi.
 *
 * NIMA QILADI. Chapda logotip, o'ngda "biz haqimizda" tugmalari.
 * Sahifa surilganda bu qator O'RNIDA QOLADI, oqim esa uning
 * OSTIDAN o'tib ketadi (loyiha egasining talabi).
 *
 * NEGA `sticky`, `fixed` EMAS. `fixed` element sahifa oqimidan
 * butunlay chiqib ketadi va uning balandligini qo'lda hisoblab,
 * pastdagi kontentga bo'shliq berish kerak bo'lardi. Balandlik esa
 * telefonda va desktopda har xil — bir joyda bo'shliq ortiqcha,
 * ikkinchisida kontent panel ostida qolib ketardi. `sticky` esa
 * avval oddiy element kabi joylashadi, keyin yopishadi.
 *
 * NEGA SHISHA YUZA. Oqim ostidan o'tayotgani KO'RINISHI kerak —
 * shunda "kirib ketdi" hissi tug'iladi. To'liq qop-qora fon bo'lsa,
 * matn shunchaki g'oyib bo'lardi. `oyna-yuza` orqa fonni xiralashtiradi
 * (`backdrop-filter`), eski brauzerda esa to'q fonga tushadi —
 * `globals.css` dagi `@supports` shuni ta'minlaydi.
 *
 * MATN TUGMA ICHIDA EMAS, PANELDA. Uch xatboshi matnni tepa qatorga
 * sig'dirib bo'lmaydi; tugma bosilganda ular panel bo'lib ochiladi.
 * Panel oqimni SURMAYDI (u `absolute`) — aks holda tugma bosilganda
 * butun sahifa sakrab ketardi.
 */

export type HaqidaBandi = {
  kod: string;
  nom: string;
  matn: string;
  belgi: IkonkaNomi;
};

export function BoshTepasi({
  nom,
  shior,
  bandlar,
  yorliq,
}: {
  nom: string;
  shior: string;
  bandlar: HaqidaBandi[];
  yorliq: { haqida: string; yopish: string };
}) {
  const [ochiq, setOchiq] = useState<string | null>(null);
  const [menyu, setMenyu] = useState(false);
  const qamrov = useRef<HTMLDivElement>(null);

  // Escape va tashqariga bosish — ikkalasi ham yopadi.
  //
  // Ansiz panel ochiq qolib, ostidagi oqimni to'sib turardi va uni
  // yopish uchun aynan o'sha tugmani topish kerak bo'lardi.
  useEffect(() => {
    if (!ochiq && !menyu) return;
    function klaviatura(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOchiq(null);
        setMenyu(false);
      }
    }
    function bosish(e: MouseEvent) {
      if (!qamrov.current?.contains(e.target as Node)) {
        setOchiq(null);
        setMenyu(false);
      }
    }
    document.addEventListener("keydown", klaviatura);
    document.addEventListener("mousedown", bosish);
    return () => {
      document.removeEventListener("keydown", klaviatura);
      document.removeEventListener("mousedown", bosish);
    };
  }, [ochiq, menyu]);

  const joriy = bandlar.find((b) => b.kod === ochiq) ?? null;

  function almashtir(kod: string) {
    setOchiq((oldingi) => (oldingi === kod ? null : kod));
    setMenyu(false);
  }

  return (
    <div
      ref={qamrov}
      // `-mx-4` va ichki `px-4`: yopishgan qator sahifa chetigacha
      // yetsin, aks holda uning yonidan oqim ko'rinib turardi.
      // `-mt-6 sm:-mt-8` — sahifaning tepa bo'shlig'ini yeb yuboradi:
      // yopishgan qator ekranning eng tepasidan boshlansin, ustida
      // bo'sh chiziq qolmasin.
      //
      // Mobil sarlavha (`Yon`) bosh sahifada chiqmaydi, shuning uchun
      // `top-0` ikkala o'lchamda ham to'g'ri.
      className="sticky top-0 z-20 -mx-4 -mt-6 mb-5 sm:-mx-6 sm:-mt-8"
    >
      <div className="oyna-yuza border-ramka-yumshoq flex items-center gap-3 border-b px-4 py-3 sm:px-6">
        {/* CHAP — logotip */}
        <Image
          src="/logo.jpg"
          alt=""
          width={44}
          height={44}
          className="rounded-tugma shrink-0"
          priority
        />
        <div className="min-w-0 flex-1">
          <p className="text-sarlavha truncate text-sm font-bold tracking-wide sm:text-base">
            {nom}
          </p>
          {/* Shior telefonda YASHIRILADI: ikki qator sarlavha
              yopishgan qatorni baland qilib, ekranni yeb qo'yardi. */}
          <p className="text-matn-past hidden truncate text-xs sm:block">
            {shior}
          </p>
        </div>

        {/* O'NG — tugmalar. Telefonda ular bitta "hamburger" ga
            yig'iladi: uchta tugma yonma-yon sig'maydi va sarlavhani
            siqib qo'yardi. */}
        <nav className="hidden shrink-0 items-center gap-1.5 md:flex">
          {bandlar.map((b) => (
            <Tugma
              key={b.kod}
              band={b}
              faol={ochiq === b.kod}
              bosildi={() => almashtir(b.kod)}
            />
          ))}
        </nav>

        <button
          type="button"
          onClick={() => {
            setMenyu((x) => !x);
            setOchiq(null);
          }}
          aria-expanded={menyu}
          aria-label={yorliq.haqida}
          className="border-ramka-yumshoq rounded-tugma hover:bg-panel-yorqin shrink-0 border p-2 transition md:hidden"
        >
          <Ikonka nom={menyu ? "yopish" : "produkt"} />
        </button>
      </div>

      {/* Telefon uchun ro'yxat */}
      {menyu && (
        <div className="oyna-panel border-ramka-yumshoq absolute inset-x-0 top-full border-b p-3 md:hidden">
          <ul className="space-y-1.5">
            {bandlar.map((b) => (
              <li key={b.kod}>
                <button
                  type="button"
                  onClick={() => almashtir(b.kod)}
                  className="hover:bg-panel-yorqin rounded-tugma flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-sm transition"
                >
                  <Ikonka nom={b.belgi} className="text-ramka h-4 w-4" />
                  {b.nom}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Ochilgan matn. `absolute` — oqimni surmaydi.
          `max-h` + `overflow-y`: uzun matn butun ekranni egallamasin
          va panel ichida surilsin. */}
      {joriy && (
        <div className="oyna-panel border-ramka-yumshoq absolute inset-x-0 top-full max-h-[60vh] overflow-y-auto border-b px-4 py-4 sm:px-6">
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 flex items-start justify-between gap-3">
              <h2 className="text-sarlavha flex items-center gap-2 font-bold">
                <Ikonka nom={joriy.belgi} className="text-ramka" />
                {joriy.nom}
              </h2>
              <button
                type="button"
                onClick={() => setOchiq(null)}
                aria-label={yorliq.yopish}
                className="border-ramka-yumshoq rounded-tugma hover:bg-panel-yorqin shrink-0 border p-1.5 transition"
              >
                <Ikonka nom="yopish" className="h-4 w-4" />
              </button>
            </div>
            <p className="text-sm leading-relaxed">{joriy.matn}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function Tugma({
  band,
  faol,
  bosildi,
}: {
  band: HaqidaBandi;
  faol: boolean;
  bosildi: () => void;
}) {
  return (
    <button
      type="button"
      onClick={bosildi}
      aria-expanded={faol}
      className={cn(
        "rounded-tugma flex items-center gap-1.5 border px-3 py-2 text-xs whitespace-nowrap transition",
        faol
          ? "border-ramka bg-panel-yorqin text-sarlavha font-semibold"
          : "border-ramka-yumshoq hover:border-ramka hover:bg-panel-yorqin",
      )}
    >
      <Ikonka nom={band.belgi} className="text-ramka h-4 w-4" />
      {band.nom}
    </button>
  );
}
