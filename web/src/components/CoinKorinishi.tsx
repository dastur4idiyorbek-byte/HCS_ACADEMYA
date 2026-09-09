"use client";

import { useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import {
  chiziqNuqtalari,
  foizRangi,
  narxMatn,
  qisqaSon,
  sarala,
  xaritaUlushi,
  type CoinHolati,
  type SaralashKaliti,
} from "@/lib/bozor";

/** Bozor holati — coinlar ro'yxatining uch ko'rinishi.
 *
 * NEGA UCHTASI HAM BOR. Uchalasi bitta savolga javob bermaydi:
 *
 *   jadval    — "aniq raqam qancha?"  (ko'p ustun, saralanadi)
 *   kartochka — "shu coin qanday?"    (telefonda qulay, yirik)
 *   xarita    — "bugun bozor qayoqqa?" (bir qarashda butun manzara)
 *
 * Tanlov brauzerda saqlanmaydi: sahifa har safar jadvaldan
 * boshlanadi. Sabab — ko'rinish tanlovi qaror emas, qarash usuli;
 * uni eslab qolish foydadan ko'ra chalkashlik keltirardi ("nega
 * boshqacha ochildi?").
 */

type Korinish = "jadval" | "kartochka" | "xarita";

const RANG: Record<"yaxshi" | "past" | "neytral", string> = {
  yaxshi: "text-yaxshi",
  past: "text-past",
  neytral: "text-matn-past",
};

/** Xarita bloklarining foni. Matn oq bo'lgani uchun to'yinganlik
 *  o'zgarishning KUCHIGA qarab ortadi — kichik tebranishda deyarli
 *  rangsiz, katta harakatda to'yingan. */
function xaritaFoni(foiz: number | null): string {
  if (foiz === null) return "color-mix(in srgb, var(--rang-panel) 80%, transparent)";
  const kuch = Math.min(Math.abs(foiz) / 8, 1);
  const asos = foiz > 0.1 ? "var(--rang-yaxshi)" : foiz < -0.1 ? "var(--rang-past-toq)" : "var(--rang-panel)";
  const ulush = Math.round(18 + kuch * 62);
  return `color-mix(in srgb, ${asos} ${ulush}%, var(--rang-panel))`;
}

function MiniGrafik({
  qiymatlar,
  foiz,
}: {
  qiymatlar: number[];
  foiz: number | null;
}) {
  const nuqtalar = chiziqNuqtalari(qiymatlar, 88, 26);
  // Ma'lumot yetarli emas — bo'sh joy qoladi. Tekis chiziq chizsak
  // "narx o'zgarmadi" degan MA'LUMOT bo'lardi, aslida bilmaymiz.
  if (nuqtalar === null) return <span className="text-matn-past text-xs">—</span>;

  const rang =
    foizRangi(foiz) === "yaxshi"
      ? "var(--rang-yaxshi)"
      : foizRangi(foiz) === "past"
        ? "var(--rang-past)"
        : "var(--rang-matn-past)";

  return (
    <svg viewBox="0 0 88 26" width="88" height="26" aria-hidden>
      <polyline
        points={nuqtalar}
        fill="none"
        stroke={rang}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Foiz({ qiymat }: { qiymat: number | null }) {
  if (qiymat === null) return <span className="text-matn-past">—</span>;
  const belgi = qiymat > 0 ? "+" : "";
  return (
    <span className={cn("raqam", RANG[foizRangi(qiymat)])}>
      {belgi}
      {qiymat.toFixed(2)}%
    </span>
  );
}

export type Yorliqlar = {
  jadval: string;
  kartochka: string;
  xarita: string;
  coin: string;
  narx: string;
  ozgarish24: string;
  ozgarish7k: string;
  kapital: string;
  hajm: string;
  yetti_kun: string;
};

export function CoinKorinishi({
  coinlar,
  yorliq,
}: {
  coinlar: CoinHolati[];
  yorliq: Yorliqlar;
}) {
  const [korinish, setKorinish] = useState<Korinish>("jadval");
  const [kalit, setKalit] = useState<SaralashKaliti>("kapital");
  const [osib, setOsib] = useState(false);

  const tartibli = useMemo(
    () => sarala(coinlar, kalit, osib),
    [coinlar, kalit, osib],
  );

  const jamiKapital = useMemo(
    () => coinlar.reduce((s, c) => s + (c.kapital ?? 0), 0),
    [coinlar],
  );

  function ustunBos(yangi: SaralashKaliti) {
    if (yangi === kalit) setOsib((x) => !x);
    else {
      setKalit(yangi);
      setOsib(false);
    }
  }

  const tugmalar: { kod: Korinish; matn: string }[] = [
    { kod: "jadval", matn: yorliq.jadval },
    { kod: "kartochka", matn: yorliq.kartochka },
    { kod: "xarita", matn: yorliq.xarita },
  ];

  return (
    <div>
      <div
        role="tablist"
        aria-label={yorliq.coin}
        className="border-ramka-yumshoq mb-4 inline-flex gap-1 rounded-kichik border p-1"
      >
        {tugmalar.map((t) => (
          <button
            key={t.kod}
            type="button"
            role="tab"
            aria-selected={korinish === t.kod}
            onClick={() => setKorinish(t.kod)}
            className={cn(
              "rounded-kichik px-3 py-1.5 text-sm transition-colors",
              korinish === t.kod
                ? "bg-panel-yorqin text-sarlavha font-semibold"
                : "text-matn-past hover:text-matn",
            )}
          >
            {t.matn}
          </button>
        ))}
      </div>

      {korinish === "jadval" && (
        <Jadval
          coinlar={tartibli}
          kalit={kalit}
          osib={osib}
          ustunBos={ustunBos}
          yorliq={yorliq}
        />
      )}
      {korinish === "kartochka" && <Kartochkalar coinlar={tartibli} yorliq={yorliq} />}
      {korinish === "xarita" && (
        <Xarita coinlar={tartibli} jamiKapital={jamiKapital} />
      )}
    </div>
  );
}

// --------------------------------------------------------------------- //
//  1. Jadval
// --------------------------------------------------------------------- //

function Jadval({
  coinlar,
  kalit,
  osib,
  ustunBos,
  yorliq,
}: {
  coinlar: CoinHolati[];
  kalit: SaralashKaliti;
  osib: boolean;
  ustunBos: (k: SaralashKaliti) => void;
  yorliq: Yorliqlar;
}) {
  const ustunlar: { kod: SaralashKaliti; matn: string }[] = [
    { kod: "narx", matn: yorliq.narx },
    { kod: "ozgarish24", matn: yorliq.ozgarish24 },
    { kod: "ozgarish7k", matn: yorliq.ozgarish7k },
    { kod: "kapital", matn: yorliq.kapital },
    { kod: "hajm24", matn: yorliq.hajm },
  ];

  return (
    // Jadval TOR ekranga sig'maydi va sig'dirishga urinish uni
    // o'qib bo'lmas holga keltiradi. Shuning uchun O'ZI siljiydi —
    // sahifaning o'zi yon tomonga surilmaydi.
    <div className="border-ramka-yumshoq rounded-kartochka overflow-x-auto border">
      <table className="w-full min-w-[46rem] text-sm">
        <thead className="text-matn-past border-ramka-yumshoq border-b text-left text-xs">
          <tr>
            <th scope="col" className="px-3 py-2.5 font-medium">
              {yorliq.coin}
            </th>
            {ustunlar.map((u) => (
              // `aria-sort` ustun sarlavhasiga tegishli, tugmaga emas:
              // ekran o'quvchi jadval qaysi ustun bo'yicha
              // saralanganini shu yerdan o'qiydi.
              <th
                key={u.kod}
                scope="col"
                aria-sort={
                  kalit === u.kod ? (osib ? "ascending" : "descending") : "none"
                }
                className="px-3 py-2.5 text-right font-medium"
              >
                <button
                  type="button"
                  onClick={() => ustunBos(u.kod)}
                  className={cn(
                    "hover:text-matn transition-colors",
                    kalit === u.kod && "text-sarlavha font-semibold",
                  )}
                >
                  {u.matn}
                  {kalit === u.kod && (osib ? " ↑" : " ↓")}
                </button>
              </th>
            ))}
            <th scope="col" className="px-3 py-2.5 text-right font-medium">
              {yorliq.yetti_kun}
            </th>
          </tr>
        </thead>
        <tbody>
          {coinlar.map((c) => (
            <tr key={c.ticker} className="border-ramka-yumshoq hover:bg-panel-yorqin border-b last:border-0">
              <th scope="row" className="px-3 py-2.5 text-left font-normal">
                <span className="text-sarlavha font-semibold">{c.ticker}</span>
                <span className="text-matn-past ml-2 text-xs">{c.nom}</span>
              </th>
              <td className="raqam px-3 py-2.5 text-right">{narxMatn(c.narx)}</td>
              <td className="px-3 py-2.5 text-right">
                <Foiz qiymat={c.ozgarish24} />
              </td>
              <td className="px-3 py-2.5 text-right">
                <Foiz qiymat={c.ozgarish7k} />
              </td>
              <td className="raqam px-3 py-2.5 text-right">
                {c.kapital === null ? "—" : `$${qisqaSon(c.kapital)}`}
              </td>
              <td className="raqam px-3 py-2.5 text-right">
                {c.hajm24 === null ? "—" : `$${qisqaSon(c.hajm24)}`}
              </td>
              <td className="px-3 py-2.5 text-right">
                <div className="flex justify-end">
                  <MiniGrafik qiymatlar={c.chiziq} foiz={c.ozgarish7k} />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --------------------------------------------------------------------- //
//  2. Kartochkalar
// --------------------------------------------------------------------- //

function Kartochkalar({
  coinlar,
  yorliq,
}: {
  coinlar: CoinHolati[];
  yorliq: Yorliqlar;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {coinlar.map((c) => (
        <div
          key={c.ticker}
          className="rounded-kartochka border-ramka-yumshoq bg-panel border p-4"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sarlavha font-semibold">{c.ticker}</p>
              <p className="text-matn-past truncate text-xs">{c.nom}</p>
            </div>
            <MiniGrafik qiymatlar={c.chiziq} foiz={c.ozgarish7k} />
          </div>

          <p className="raqam mt-3 text-lg">{narxMatn(c.narx)}</p>

          <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
            <dt className="text-matn-past">{yorliq.ozgarish24}</dt>
            <dd className="text-right">
              <Foiz qiymat={c.ozgarish24} />
            </dd>
            <dt className="text-matn-past">{yorliq.ozgarish7k}</dt>
            <dd className="text-right">
              <Foiz qiymat={c.ozgarish7k} />
            </dd>
            <dt className="text-matn-past">{yorliq.kapital}</dt>
            <dd className="raqam text-right">
              {c.kapital === null ? "—" : `$${qisqaSon(c.kapital)}`}
            </dd>
          </dl>
        </div>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------- //
//  3. Issiqlik xaritasi
// --------------------------------------------------------------------- //

function Xarita({
  coinlar,
  jamiKapital,
}: {
  coinlar: CoinHolati[];
  jamiKapital: number;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {coinlar.map((c) => {
        const ulush = xaritaUlushi(c.kapital, jamiKapital);
        // Eng kichigi ham bosiladigan va o'qiladigan bo'lib qolsin:
        // 72px — barmoq uchun tavsiya etilgan eng kam o'lchamga yaqin.
        const en = Math.max(72, Math.round(ulush * 420));
        return (
          <div
            key={c.ticker}
            style={{ width: en, background: xaritaFoni(c.ozgarish24) }}
            className="rounded-kichik border-ramka-yumshoq flex min-h-[72px] flex-col justify-center border px-2 py-2 text-center"
          >
            <span className="text-sarlavha text-sm font-semibold">
              {c.ticker}
            </span>
            <span className="raqam mt-0.5 text-xs">
              {c.ozgarish24 === null
                ? "—"
                : `${c.ozgarish24 > 0 ? "+" : ""}${c.ozgarish24.toFixed(1)}%`}
            </span>
          </div>
        );
      })}
    </div>
  );
}
