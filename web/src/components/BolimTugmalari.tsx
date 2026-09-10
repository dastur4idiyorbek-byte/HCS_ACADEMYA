"use client";

import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";

/** Sahifa ichidagi bo'limlarga o'tish tugmalari.
 *
 * NEGA KERAK. Bozor holati uzun sahifa: salomatlik, sektorlar,
 * terminallar, coinlar. Telefonda coinlar ro'yxatiga yetish uchun
 * uzoq surish kerak. Bu qator o'sha yo'lni bitta bosishga
 * qisqartiradi.
 *
 * NEGA MENYU TAKRORI EMAS. Pastki nav SAHIFALAR orasida yuradi, bu
 * esa BITTA sahifaning ichida. Ikkalasi boshqa ish qiladi.
 *
 * NEGA ODDIY HAVOLA. `#langar` — brauzerning o'z imkoniyati: JS
 * o'chiq bo'lsa ham ishlaydi va orqaga qaytish tugmasi to'g'ri
 * yuradi. `scroll-margin-top` bo'limlarda beriladi, aks holda
 * sarlavha ekran chetiga yopishib qolardi.
 */
export function BolimTugmalari({
  bolimlar,
}: {
  bolimlar: { langar: string; nom: string; belgi?: IkonkaNomi }[];
}) {
  return (
    <nav
      aria-label="Sahifa bo'limlari"
      className="mb-5 flex gap-2 overflow-x-auto pb-1"
    >
      {bolimlar.map((b) => (
        <a
          key={b.langar}
          href={`#${b.langar}`}
          className="rounded-kichik border-ramka-yumshoq hover:border-ramka hover:bg-panel-yorqin flex shrink-0 items-center gap-2 border bg-white/[0.02] px-4 py-2.5 text-[13px] whitespace-nowrap transition-colors"
        >
          {b.belgi && <Ikonka nom={b.belgi} className="text-ramka h-4 w-4" />}
          {b.nom}
        </a>
      ))}
    </nav>
  );
}
