import Link from "next/link";

import { Ikonka } from "@/components/ui/Ikonka";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Modul — tahlil modullarining umumiy sahifasi.
 *
 * Har bir versiya alohida bo'lim bo'lib turadi:
 *
 *   - Modul 3.0.0 — mavjud kuzatuv. Admin kuzatuv paneliga,
 *     foydalanuvchi coin qidirishga tushadi (panel adminga xos).
 *   - Modul 4.0.0 — portlash xavfi radari, FAQAT ADMIN uchun
 *     (`docs/MODUL_4_0_0.md`). Foydalanuvchiga kartochka umuman
 *     ko'rinmaydi.
 *
 * Sahifa FAQAT YO'L KO'RSATADI: hech qanday ma'lumot yuklamaydi.
 * Kuzatuv paneli ham, radar sahifasi ham admin huquqini qayta
 * tekshiradi.
 */
export default async function Modul() {
  const { til, admin } = await kirim();
  const t = tarjimon(til);

  return (
    <>
      <Sarlavha
        matn={t("modul.sarlavha")}
        izoh={t("modul.izoh")}
        belgi="korish"
      />

      <div className="grid gap-3 sm:grid-cols-2">
        <ModulKartochka
          yol={admin ? "/kuzatuv" : "/qidiruv"}
          nom={t("modul.v3")}
          izoh={t("modul.v3_izoh")}
          tugma={t("modul.ochish")}
        />
        {admin ? (
          <ModulKartochka
            yol="/modul-4"
            nom={t("modul.v4")}
            izoh={t("modul.v4_izoh")}
            tugma={t("modul.ochish")}
          />
        ) : null}
      </div>
    </>
  );
}

function ModulKartochka({
  yol,
  nom,
  izoh,
  tugma,
  belgi,
}: {
  yol: string;
  nom: string;
  izoh: string;
  tugma?: string;
  belgi?: React.ReactNode;
}) {
  return (
    <Link
      href={yol}
      className="rounded-kartochka border-ramka-yumshoq hover:border-ramka hover:bg-panel-yorqin flex flex-col border bg-white/[0.02] p-5 transition-colors"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-sarlavha flex items-center gap-2 text-lg font-bold">
          <Ikonka nom="korish" className="text-ramka h-6 w-6" />
          {nom}
        </span>
        {belgi}
      </div>
      <p className="text-matn-past mt-2 text-sm leading-relaxed">{izoh}</p>
      {tugma && (
        <span className="text-sarlavha mt-auto pt-4 text-sm font-semibold">
          {tugma} →
        </span>
      )}
    </Link>
  );
}
