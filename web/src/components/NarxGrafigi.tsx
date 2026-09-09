"use client";

import { useState } from "react";

import { Grafik } from "@/components/Grafik";
import { cn } from "@/lib/cn";
import { foizRangi, narxMatn, type CoinHolati } from "@/lib/bozor";

/** Real narx grafigi — coin tanlanadi, grafik DARROV ko'rinadi.
 *
 * NEGA QAYTA YOZILDI. Ilgari bu yerda toifalar va coin "chiplari"
 * ro'yxati turardi, grafik esa faqat coin BOSILGANDA ochilardi.
 * Sahifada "Real narx terminallari" degan sarlavha bor edi-yu,
 * grafik yo'q edi — foydalanuvchi uni ko'rmasdi va bo'lim nima uchun
 * borligini tushunmasdi.
 *
 * Endi grafik boshidanoq turadi (BTC), coin esa ustidagi qatordan
 * almashtiriladi — birjadagi kabi.
 *
 * BITTA GRAFIK, KO'P EMAS. O'nlab TradingView widgeti bitta sahifada
 * — o'nlab `iframe` va tashqi skript; telefonda sahifa amalda
 * ochilmasdi. Shuning uchun bitta grafik va tanlovchi.
 *
 * FAQAT HALOL RO'YXAT: tanlovchida `docs/HALOL_ROYXAT.md` dagi
 * coinlardan tashqarisi yo'q.
 */
export function NarxGrafigi({
  coinlar,
  xatoMatni,
  qidirMatni,
}: {
  coinlar: CoinHolati[];
  xatoMatni: string;
  qidirMatni: string;
}) {
  const [tanlangan, setTanlangan] = useState("BTC");
  const [qidiruv, setQidiruv] = useState("");

  const izlangan = qidiruv.trim().toLowerCase();
  const korinadigan =
    izlangan === ""
      ? coinlar
      : coinlar.filter(
          (c) =>
            c.ticker.toLowerCase().includes(izlangan) ||
            c.nom.toLowerCase().includes(izlangan),
        );

  const joriy = coinlar.find((c) => c.ticker === tanlangan);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-sarlavha text-lg font-bold">
          {tanlangan}/USDT
        </span>
        {joriy && (
          <>
            <span className="raqam text-lg">{narxMatn(joriy.narx)}</span>
            {joriy.ozgarish24 !== null && (
              <span
                className={cn(
                  "raqam text-sm",
                  foizRangi(joriy.ozgarish24) === "yaxshi"
                    ? "text-yaxshi"
                    : foizRangi(joriy.ozgarish24) === "past"
                      ? "text-past"
                      : "text-matn-past",
                )}
              >
                {joriy.ozgarish24 > 0 ? "+" : ""}
                {joriy.ozgarish24.toFixed(2)}%
              </span>
            )}
          </>
        )}
      </div>

      <input
        type="search"
        value={qidiruv}
        onChange={(e) => setQidiruv(e.target.value)}
        placeholder={qidirMatni}
        aria-label={qidirMatni}
        className="border-ramka-yumshoq rounded-kichik bg-panel placeholder:text-matn-past focus:border-ramka mb-2 w-full max-w-[15rem] border px-3 py-1.5 text-[13px] outline-none"
      />

      {/* Coin tanlovchi. Gorizontal siljiydi: 80 ta coin hech qanday
          ekranga sig'maydi va ularni ustma-ust terish grafikni
          pastga surib yuborardi. */}
      <div className="mb-3 flex gap-1.5 overflow-x-auto pb-1">
        {korinadigan.map((c) => (
          <button
            key={c.ticker}
            type="button"
            onClick={() => setTanlangan(c.ticker)}
            aria-pressed={tanlangan === c.ticker}
            className={cn(
              "rounded-kichik shrink-0 border px-2.5 py-1.5 text-xs whitespace-nowrap transition-colors",
              tanlangan === c.ticker
                ? "border-ramka bg-panel-yorqin text-sarlavha font-semibold"
                : "border-ramka-yumshoq text-matn-past hover:text-matn",
            )}
          >
            {c.ticker}
          </button>
        ))}
      </div>

      {/* `key` — coin almashganda widget QAYTADAN qurilsin.
          TradingView `symbol` ni keyinchalik o'zgartirishga ruxsat
          bermaydi, eski grafik esa joyida qolib ketardi. */}
      <Grafik
        key={tanlangan}
        symbol={`BINANCE:${tanlangan}USDT`}
        xatoMatni={xatoMatni}
      />
    </div>
  );
}
