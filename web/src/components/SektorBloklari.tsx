import { cn } from "@/lib/cn";
import { foizRangi, qisqaSon, treemap, type SektorHolati } from "@/lib/bozor";

/** Sektorlar — tepada treemap, pastda ro'yxat.
 *
 * NEGA IKKALASI. Ular ikki xil savolga javob beradi: xarita "bugun
 * qaysi sektor qizib turibdi?" degan bir qarashlik savolga, ro'yxat
 * esa "aniq qancha?" degan savolga. Bittasini tashlab ketsak, o'sha
 * savol javobsiz qolardi.
 *
 * SERVER KOMPONENTI: bu yerda tanlov yo'q — saralash ham, ko'rinish
 * almashtirish ham. Klientga JavaScript yubormaymiz.
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
  return `color-mix(in srgb, ${asos} ${Math.round(16 + kuch * 64)}%, var(--rang-panel))`;
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

  const kataklar = treemap(
    sektorlar.map((s) => ({ kalit: s.id, ogirlik: s.kapital ?? 0 })),
  );
  const boyicha = new Map(sektorlar.map((s) => [s.id, s]));

  return (
    <div className="space-y-4">
      {kataklar.length > 0 && (
        <div className="relative h-[18rem] w-full sm:h-[22rem]">
          {kataklar.map((k) => {
            const s = boyicha.get(k.kalit);
            if (!s) return null;
            const torgina = k.en < 9 || k.boy < 11;
            return (
              <div
                key={k.kalit}
                title={s.nom}
                style={{
                  left: `${k.x}%`,
                  top: `${k.y}%`,
                  width: `${k.en}%`,
                  height: `${k.boy}%`,
                  background: foni(s.ozgarish24),
                }}
                className="rounded-kichik absolute flex flex-col items-center justify-center overflow-hidden border border-white/10 p-1 text-center"
              >
                <span className="text-sarlavha line-clamp-2 text-[10px] leading-tight font-semibold sm:text-[11px]">
                  {s.nom}
                </span>
                {!torgina && (
                  <span className="raqam mt-0.5 text-[10px] leading-tight">
                    {s.ozgarish24 === null
                      ? "—"
                      : `${s.ozgarish24 > 0 ? "+" : ""}${s.ozgarish24.toFixed(1)}%`}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="-mx-4 overflow-x-auto sm:mx-0">
        <table className="w-full min-w-[26rem] text-[13px]">
          <thead className="text-matn-past border-b border-white/10 text-left text-[11px] tracking-wide uppercase">
            <tr>
              <th scope="col" className="w-10 px-3 py-2 text-right font-medium">
                #
              </th>
              <th scope="col" className="px-2 py-2 font-medium">
                {yorliq.sektor}
              </th>
              <th scope="col" className="px-3 py-2 text-right font-medium">
                {yorliq.kapital}
              </th>
              <th scope="col" className="px-3 py-2 text-right font-medium">
                {yorliq.ozgarish24}
              </th>
            </tr>
          </thead>
          <tbody>
            {sektorlar.map((s, i) => (
              <tr
                key={s.id}
                className="hover:bg-panel-yorqin border-b border-white/5 transition-colors last:border-0"
              >
                <td className="raqam text-matn-past px-3 py-2 text-right">
                  {i + 1}
                </td>
                <th scope="row" className="px-2 py-2 text-left font-normal">
                  {s.nom}
                </th>
                <td className="raqam px-3 py-2 text-right whitespace-nowrap">
                  {s.kapital === null ? "—" : `$${qisqaSon(s.kapital)}`}
                </td>
                <td
                  className={cn(
                    "raqam px-3 py-2 text-right whitespace-nowrap",
                    RANG[foizRangi(s.ozgarish24)],
                  )}
                >
                  {s.ozgarish24 === null ? (
                    "—"
                  ) : (
                    <>
                      <span aria-hidden className="mr-0.5 text-[9px]">
                        {s.ozgarish24 > 0.1 ? "▲" : s.ozgarish24 < -0.1 ? "▼" : "•"}
                      </span>
                      {Math.abs(s.ozgarish24).toFixed(2)}%
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
