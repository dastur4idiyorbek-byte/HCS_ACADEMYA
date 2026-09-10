"use client";

import { useEffect, useRef, useState } from "react";

import { Ikonka } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";
import { suvBelgisiUslubi } from "@/lib/himoya";

/** Signal narxlarini himoyalash qatlami.
 *
 * ROSTINI AYTGANDA: brauzerda skrinshotni TO'LIQ to'sib bo'lmaydi.
 * Telegramdagi `protect_content` kabi narsa vebda mavjud emas — bu
 * brauzer imkoniyati emas, operatsion tizim darajasidagi cheklov.
 * Yonidagi ikkinchi telefon bilan ekranni suratga olishni esa hech
 * qanday texnologiya to'xtata olmaydi.
 *
 * Shuning uchun bu yerda uchta QATLAM bor, har biri boshqa ishni
 * bajaradi:
 *
 *   1. FOKUS YO'QOLGANDA XIRALASHTIRISH — eng ko'p uchraydigan holatni
 *      tutadi. Windowsda `Win+Shift+S`, macOS'da `Cmd+Shift+4`,
 *      telefonda esa boshqa ilovaga o'tish — hammasi sahifadan fokusni
 *      OLADI. Shu lahzada narxlar xiralashadi va skrinshotga tushmaydi.
 *      `PrintScreen` tugmasi bundan mustasno: u fokusni olmaydi.
 *
 *   2. SUV BELGISI — foydalanuvchining Telegram ID si narxlar ustida
 *      turadi. Bu nusxalashni TO'XTATMAYDI, lekin tarqatgan odamni
 *      aniqlab beradi. Pullik signal xizmatlarida aynan shu eng kuchli
 *      to'siq: skrinshot chiqadi-yu, unda kimning IDsi turgani ko'rinadi.
 *
 *   3. NUSXALASH VA CHOP ETISHNI BLOKLASH — matnni belgilab olish,
 *      `Ctrl+C` va `Ctrl+P` ishlamaydi. Skrinshotdan himoya emas, lekin
 *      eng oson yo'lni yopadi.
 *
 * Qatlamlar bir-birini to'ldiradi, lekin kafolat bermaydi — buni
 * foydalanuvchiga ham, o'zimizga ham yashirmaslik kerak.
 */
export function Himoya({
  belgi,
  ogohlantirish,
  children,
}: {
  /** Suv belgisida ko'rinadigan matn — foydalanuvchi IDsi */
  belgi: string;
  /** Xiralashgan holatda chiqadigan matn */
  ogohlantirish: string;
  children: React.ReactNode;
}) {
  const [yashirin, setYashirin] = useState(false);
  const oxirgi = useRef(0);

  useEffect(() => {
    // Fokus qaytganda darhol ochmaymiz: skrinshot vositasi oynani
    // yopgan zahoti fokus qaytadi, ekranda esa hali eski kadr turishi
    // mumkin. Kichik kechikish shu oraliqni yopadi.
    let taymer: ReturnType<typeof setTimeout> | undefined;

    const yop = () => {
      oxirgi.current = Date.now();
      clearTimeout(taymer);
      setYashirin(true);
    };
    const och = () => {
      clearTimeout(taymer);
      taymer = setTimeout(() => setYashirin(false), 350);
    };

    const korinish = () =>
      document.visibilityState === "hidden" ? yop() : och();

    window.addEventListener("blur", yop);
    window.addEventListener("focus", och);
    document.addEventListener("visibilitychange", korinish);

    return () => {
      clearTimeout(taymer);
      window.removeEventListener("blur", yop);
      window.removeEventListener("focus", och);
      document.removeEventListener("visibilitychange", korinish);
    };
  }, []);

  return (
    <div className="himoya relative">
      <div
        className={cn(
          "transition-[filter,opacity] duration-150",
          yashirin && "pointer-events-none opacity-40 blur-lg select-none",
        )}
        onCopy={(e) => e.preventDefault()}
        onCut={(e) => e.preventDefault()}
        onContextMenu={(e) => e.preventDefault()}
      >
        {children}
        <span
          aria-hidden
          className="suv-belgisi"
          style={suvBelgisiUslubi(belgi)}
        />
      </div>

      {yashirin && (
        <div className="absolute inset-0 flex items-center justify-center p-4">
          <p className="border-ramka bg-fon rounded-kartochka border px-4 py-3 text-center text-sm">
            <Ikonka nom="qulf" className="inline h-4 w-4 align-[-3px]" />{" "}
            {ogohlantirish}
          </p>
        </div>
      )}
    </div>
  );
}
