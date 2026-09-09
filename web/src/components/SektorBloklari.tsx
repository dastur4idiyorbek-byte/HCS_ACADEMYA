import { cn } from "@/lib/cn";
import { foizRangi, qisqaSon, xaritaUlushi, type SektorHolati } from "@/lib/bozor";

/** Sektorlar — tepada xarita, pastda ro'yxat.
 *
 * NEGA IKKALASI. Ular ikki xil savolga javob beradi: xarita "bugun
 * qaysi sektor qizib turibdi?" degan bir qarashlik savolga, ro'yxat
 * esa "aniq qancha?" degan savolga. Bittasini tashlab ketsak, o'sha
 * savol javobsiz qolardi.
 *
 * SERVER KOMPONENTI: bu yerda hech qanday tanlov yo'q — saralash ham,
 * ko'rinish almashtirish ham. Klientga JavaScript yubormaymiz.
 */

function foni(foiz: number | null): string {
  if (foiz === null) {
    return "color-mix(in srgb, var(--rang-panel) 80%, transparent)";
  }
  const kuch = Math.min(Math.abs(foiz) / 8, 1);
  const asos =
    foiz > 0.1
      ? "var(--rang-yaxshi)"
      : foiz < -0.1
        ? "var(--rang-past-toq)"
        : "var(--rang-panel)";
  return `color-mix(in srgb, ${asos} ${Math.round(18 + kuch * 62)}%, var(--rang-panel))`;
}

const RANG = {
  yaxshi: "text-yaxshi",
  past: "text-past",
  neytral: "text-matn-past",
} as const;

export function SektorBloklari({
  sektorlar,
  yorliq,
}: {
  sektorlar: SektorHolati[];
  yorliq: { sektor: string; kapital: string; ozgarish24: string };
}) {
  if (sektorlar.length === 0) return null;

  const jami = sektorlar.reduce((s, x) => s + (x.kapital ?? 0), 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1.5">
        {sektorlar.map((s) => {
          const en = Math.max(84, Math.round(xaritaUlushi(s.kapital, jami) * 400));
          return (
            <div
              key={s.id}
              style={{ width: en, background: foni(s.ozgarish24) }}
              className="rounded-kichik border-ramka-yumshoq flex min-h-[68px] flex-col justify-center border px-2 py-2 text-center"
            >
              <span className="text-sarlavha text-xs leading-tight font-semibold">
                {s.nom}
              </span>
              <span className="raqam mt-1 text-xs">
                {s.ozgarish24 === null
                  ? "—"
                  : `${s.ozgarish24 > 0 ? "+" : ""}${s.ozgarish24.toFixed(1)}%`}
              </span>
            </div>
          );
        })}
      </div>

      <div className="border-ramka-yumshoq rounded-kartochka overflow-x-auto border">
        <table className="w-full min-w-[26rem] text-sm">
          <thead className="text-matn-past border-ramka-yumshoq border-b text-left text-xs">
            <tr>
              <th scope="col" className="px-3 py-2.5 font-medium">
                {yorliq.sektor}
              </th>
              <th scope="col" className="px-3 py-2.5 text-right font-medium">
                {yorliq.kapital}
              </th>
              <th scope="col" className="px-3 py-2.5 text-right font-medium">
                {yorliq.ozgarish24}
              </th>
            </tr>
          </thead>
          <tbody>
            {sektorlar.map((s) => (
              <tr
                key={s.id}
                className="border-ramka-yumshoq hover:bg-panel-yorqin border-b last:border-0"
              >
                <th scope="row" className="px-3 py-2.5 text-left font-normal">
                  {s.nom}
                </th>
                <td className="raqam px-3 py-2.5 text-right">
                  {s.kapital === null ? "—" : `$${qisqaSon(s.kapital)}`}
                </td>
                <td
                  className={cn(
                    "raqam px-3 py-2.5 text-right",
                    RANG[foizRangi(s.ozgarish24)],
                  )}
                >
                  {s.ozgarish24 === null
                    ? "—"
                    : `${s.ozgarish24 > 0 ? "+" : ""}${s.ozgarish24.toFixed(2)}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
