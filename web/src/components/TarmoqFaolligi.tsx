import { qisqaSon, type CoinHolati } from "@/lib/bozor";
import type { TarmoqFaolligi as Faollik } from "@/lib/bozor-server";

/** On-chain: tarmoq faolligi.
 *
 * NEGA NARXDAN KEYIN TURADI. Narx savdodan keladi, bu raqamlar esa
 * tarmoqning o'zidan. Ular boshqa savolga javob beradi: coin
 * HAQIQATAN ishlatilyaptimi. Ikkalasini yonma-yon qo'yish
 * foydalanuvchini "narx = foydalanish" degan xato xulosaga
 * olib kelardi.
 */
export function TarmoqFaolligi({
  tarmoqlar,
  coinlar,
  yorliq,
}: {
  tarmoqlar: Faollik[];
  coinlar: CoinHolati[];
  yorliq: { tarmoq: string; tranzaksiya: string; blok: string; komissiya: string };
}) {
  if (tarmoqlar.length === 0) return null;
  const logotip = new Map(coinlar.map((c) => [c.ticker, c.logo]));

  return (
    <div className="-mx-4 overflow-x-auto sm:mx-0">
      <table className="w-full min-w-[32rem] text-[13px]">
        <thead className="text-matn-past border-b border-white/10 text-left text-[11px] tracking-wide uppercase">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">
              {yorliq.tarmoq}
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              {yorliq.tranzaksiya}
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              {yorliq.blok}
            </th>
            <th scope="col" className="px-3 py-2 text-right font-medium">
              {yorliq.komissiya}
            </th>
          </tr>
        </thead>
        <tbody>
          {tarmoqlar.map((tarmoq) => {
            const logo = logotip.get(tarmoq.ticker) ?? null;
            return (
              <tr
                key={tarmoq.ticker}
                className="hover:bg-panel-yorqin border-b border-white/5 transition-colors last:border-0"
              >
                <th scope="row" className="px-3 py-2.5 text-left font-normal">
                  <span className="flex items-center gap-2">
                    {logo === null ? (
                      <span
                        aria-hidden
                        className="bg-panel-yorqin text-matn-past inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-semibold"
                      >
                        {tarmoq.ticker.slice(0, 2)}
                      </span>
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={logo}
                        alt=""
                        width={20}
                        height={20}
                        loading="lazy"
                        className="shrink-0 rounded-full"
                      />
                    )}
                    <span className="text-sarlavha font-semibold">
                      {tarmoq.ticker}
                    </span>
                    <span className="text-matn-past hidden text-xs sm:inline">
                      {tarmoq.nom}
                    </span>
                  </span>
                </th>
                <td className="raqam px-3 py-2.5 text-right">
                  {tarmoq.tranzaksiya24 === null
                    ? "—"
                    : qisqaSon(tarmoq.tranzaksiya24)}
                </td>
                <td className="raqam px-3 py-2.5 text-right">
                  {tarmoq.blok24 === null ? "—" : tarmoq.blok24.toLocaleString()}
                </td>
                <td className="raqam px-3 py-2.5 text-right">
                  {tarmoq.ortachaKomissiya === null
                    ? "—"
                    : `$${tarmoq.ortachaKomissiya.toFixed(2)}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
