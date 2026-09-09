import Image from "next/image";

import { qisqaSon, type CoinHolati } from "@/lib/bozor";
import type { BlokcheynHolati } from "@/lib/bozor-server";

/** Blokcheynlar — tarmoqda bog'langan mablag' (TVL).
 *
 * NEGA KAPITAL EMAS, TVL. Tarmoqning "kapitali" — bu uning
 * coinining narxi va u coinlar jadvalida allaqachon bor. TVL esa
 * boshqa savolga javob beradi: shu tarmoqda qancha pul HAQIQATAN
 * ishlayapti. Ikkalasi bir xil bo'lmaydi — narxi yuqori, lekin
 * ishlatilmaydigan tarmoq ham bor.
 */
export function Blokcheynlar({
  zanjirlar,
  coinlar,
  yorliq,
}: {
  zanjirlar: BlokcheynHolati[];
  coinlar: CoinHolati[];
  yorliq: { tvl: string };
}) {
  if (zanjirlar.length === 0) return null;
  const logotip = new Map(coinlar.map((c) => [c.ticker, c.logo]));

  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
      {zanjirlar.slice(0, 8).map((z) => {
        const logo = logotip.get(z.ticker) ?? null;
        return (
          <div
            key={z.ticker}
            className="rounded-kartochka hover:border-ramka border border-white/10 bg-white/[0.02] p-3 transition-colors"
          >
            <div className="flex items-center gap-2">
              {logo === null ? (
                <span
                  aria-hidden
                  className="bg-panel-yorqin text-matn-past inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-semibold"
                >
                  {z.ticker.slice(0, 2)}
                </span>
              ) : (
                <Image
                  src={logo}
                  alt=""
                  width={20}
                  height={20}
                  unoptimized
                  className="shrink-0 rounded-full"
                />
              )}
              <p className="text-sarlavha truncate text-[13px] font-semibold">
                {z.nom}
              </p>
            </div>
            <p className="text-matn-past mt-2 text-[11px] tracking-wide uppercase">
              {yorliq.tvl}
            </p>
            <p className="raqam mt-0.5 text-base leading-none">
              {z.tvl === null ? "—" : `$${qisqaSon(z.tvl)}`}
            </p>
          </div>
        );
      })}
    </div>
  );
}
