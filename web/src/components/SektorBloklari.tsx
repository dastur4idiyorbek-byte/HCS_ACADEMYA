import { cn } from "@/lib/cn";
import { foizRangi, qisqaSon, type SektorHolati } from "@/lib/bozor";

/** Sektorlar — kartochkalar va ro'yxat.
 *
 * NEGA TREEMAP EMAS (u bor edi va OLIB TASHLANDI). Treemap butunni
 * bo'laklarga bo'ladi: har bir to'rtburchak "butunning shuncha
 * qismi" degan ma'noni beradi. CoinGecko toifalari esa bo'lak emas —
 * ular ustma-ust tushadi va bitta coin o'nlab toifada bo'ladi.
 *
 * Amalda bu shunday ko'rindi: "Smart Contract Platform" $2.33T va
 * "Layer 1" $2.29T — deyarli bir xil coinlar, ikki marta sanalgan.
 * Butun bozor esa $2.71T. Ya'ni bo'laklar yig'indisi butundan katta
 * chiqardi va xarita YOLG'ON gapirardi.
 *
 * Kartochka bunday da'vo qilmaydi: u faqat "shu sektorning kapitali
 * shuncha" deydi va ustma-ust tushishi mumkinligi izohda yozilgan.
 */

const RANG = {
  yaxshi: "text-yaxshi",
  past: "text-past",
  neytral: "text-matn-past",
} as const;

function Ozgarish({ foiz }: { foiz: number | null }) {
  if (foiz === null) return <span className="text-matn-past">—</span>;
  const rol = foizRangi(foiz);
  return (
    <span className={cn("raqam whitespace-nowrap", RANG[rol])}>
      <span aria-hidden className="mr-0.5 text-[9px]">
        {rol === "yaxshi" ? "▲" : rol === "past" ? "▼" : "•"}
      </span>
      {Math.abs(foiz).toFixed(2)}%
    </span>
  );
}

export function SektorBloklari({
  sektorlar,
  yorliq,
}: {
  sektorlar: SektorHolati[];
  yorliq: { sektor: string; kapital: string; ozgarish24: string };
}) {
  if (sektorlar.length === 0) return null;

  return (
    <div className="space-y-4">
      {/* Kartochkalar — telefonda yon tomonga siljiydi, kengroq
          ekranda to'rt ustunga yotadi. */}
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
        {sektorlar.slice(0, 8).map((s) => (
          <div
            key={s.id}
            className="rounded-kartochka hover:border-ramka border border-white/10 bg-white/[0.02] p-3 transition-colors"
          >
            <p className="text-sarlavha truncate text-[13px] font-semibold">
              {s.nom}
            </p>
            <p className="raqam mt-1.5 text-base leading-none">
              {s.kapital === null ? "—" : `$${qisqaSon(s.kapital)}`}
            </p>
            <p className="mt-1.5 text-xs">
              <Ozgarish foiz={s.ozgarish24} />
            </p>
          </div>
        ))}
      </div>

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
                <td className="px-3 py-2 text-right">
                  <Ozgarish foiz={s.ozgarish24} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
