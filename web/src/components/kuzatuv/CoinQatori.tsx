import Link from "next/link";

import { Ikonka } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";
import { type KuzatuvCoin, yonalishBelgisi, zonaJoyi } from "@/lib/kuzatuv";

import { Segmentlar } from "./Segmentlar";

/** `tarjimon(til)` qaytaradigan funksiya. */
type Tarjimon = (kalit: string) => string;

/** Panel ro'yxatidagi bitta coin.
 *
 * IKKI DARAJA (5.1-qism): `kichik` — "+10" ro'yxati uchun. U
 * kichikroq va xiraroq bo'ladi, admin e'tibori tabiiy ravishda
 * avvalo Top 20 ga qaratilsin.
 *
 * MATN EMAS, IKONKA (5.2-qism): yo'nalish va zona — vizual belgi.
 * Matn yonida turadi, lekin asosiy ko'rinish — rang va shakl.
 *
 * CHEGARA: bu yerda hech qanday narx ko'rsatilmaydi. Zona rangi
 * "arzon/qimmat" deydi, lekin "shu yerdan kiring" demaydi.
 */
export function CoinQatori({
  coin,
  t,
  kichik = false,
}: {
  coin: KuzatuvCoin;
  t: Tarjimon;
  kichik?: boolean;
}) {
  // JORIY narx zonaning qayerida — zona MARKAZI emas.
  //
  // Birinchi yozuvda bu yerga zona markazi berilgan edi va ustun
  // har doim "o'rtada" ko'rsatardi: markazning nisbati doim 0.5.
  // Ya'ni ustun umuman hech narsa aytmasdi. Joriy narx endi
  // bazada saqlanadi va ustun haqiqiy javob beradi.
  const joy = zonaJoyi(coin.narx, coin.zonaPast, coin.zonaYuqori);
  const zonaRang =
    joy === "discount"
      ? "text-yaxshi"
      : joy === "premium"
        ? "text-past"
        : joy === "ortada"
          ? "text-ortacha"
          : "text-matn-past";

  return (
    <Link
      href={`/kuzatuv/${coin.symbol.toLowerCase()}`}
      className={cn(
        "rounded-kartochka border-ramka-yumshoq hover:border-ramka flex items-center gap-3 border transition-colors",
        kichik ? "bg-panel/60 p-2.5 opacity-80 hover:opacity-100" : "bg-panel p-3",
      )}
    >
      <span
        className={cn(
          "text-matn-past tabular-nums",
          kichik ? "w-5 text-[11px]" : "w-6 text-xs",
        )}
      >
        {coin.orin ?? "—"}
      </span>

      <span className="flex min-w-0 flex-1 items-center gap-2">
        <Ikonka
          nom={yonalishBelgisi(coin.yonalish)}
          className={cn(
            coin.yonalish === "uptrend" ? "text-yaxshi" : "text-sarlavha",
            kichik ? "h-3.5 w-3.5" : "h-4 w-4",
          )}
          nomi={t(`kuzatuv.yonalish.${coin.yonalish}`)}
        />
        <span className={cn("truncate font-semibold", kichik ? "text-sm" : "")}>
          {coin.symbol}
        </span>
        {coin.ogohlantirish ? (
          <Ikonka
            nom="ogohlantirish"
            className="text-ortacha h-3.5 w-3.5 shrink-0"
            nomi={t("kuzatuv.ogohlantirish")}
          />
        ) : null}
      </span>

      <span
        className={cn(
          "hidden shrink-0 sm:inline",
          zonaRang,
          kichik ? "text-[11px]" : "text-xs",
        )}
      >
        {t(`kuzatuv.zona.${joy}`)}
      </span>

      <Segmentlar segmentlar={coin.segmentlar} kichik={kichik} className="shrink-0" />

      <Ikonka nom="ochish" className="text-matn-past h-4 w-4 shrink-0" />
    </Link>
  );
}
