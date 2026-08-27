"use client";

import { suvBelgisiUslubi } from "@/lib/himoya";

/** Saytdagi video darslik pleyeri.
 *
 * HIMOYA HAQIDA ROSTINI AYTGANDA: brauzerda videoni ekrandan yozib
 * olishni to'sib bo'lmaydi. `controlsList="nodownload"` yuklab olish
 * tugmasini yashiradi, o'ng tugma bloklanadi — bu eng oson yo'llarni
 * yopadi, xolos. Kuchli to'siq boshqasi: video ustida foydalanuvchining
 * Telegram IDsi turadi, ya'ni yozib olingan nusxa kimdan chiqqani
 * ko'rinadi.
 *
 * SIGNALLARDAN FARQI: bu yerda fokus yo'qolganda XIRALASHTIRISH YO'Q.
 * Sabab amaliy — darsni tinglab turib boshqa oynaga o'tish odatiy hol,
 * har safar ekranni yopish foydali himoya emas, xalaqit. Signal narxi
 * esa bir qarashda o'qib olinadi, u yerda xiralashtirish o'rinli.
 *
 * Faylning o'zi `/api/video/[id]` orqali beriladi: har so'rovda obuna
 * tekshiriladi, ya'ni manzilni birovga berish ish bermaydi.
 */
export function VideoPleyer({
  darsId,
  belgi,
}: {
  darsId: number;
  /** Suv belgisidagi matn — foydalanuvchi IDsi */
  belgi: string;
}) {
  return (
    <div className="rounded-kartochka relative overflow-hidden">
      <video
        controls
        preload="metadata"
        controlsList="nodownload noplaybackrate"
        disablePictureInPicture
        onContextMenu={(e) => e.preventDefault()}
        className="block h-auto w-full"
        src={`/api/video/${darsId}`}
      />
      <span
        aria-hidden
        className="suv-belgisi pointer-events-none"
        style={suvBelgisiUslubi(belgi)}
      />
    </div>
  );
}
