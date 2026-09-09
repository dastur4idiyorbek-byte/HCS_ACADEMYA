"use client";

import Image from "next/image";
import { useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import {
  chiziqMaydoni,
  chiziqNuqtalari,
  foizRangi,
  narxMatn,
  qisqaSon,
  sarala,
  treemap,
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
 * KO'RINISH TANLOVI SAQLANMAYDI: sahifa har safar jadvaldan
 * boshlanadi. Tanlov qaror emas, qarash usuli; uni eslab qolish
 * foydadan ko'ra chalkashlik keltirardi ("nega boshqacha ochildi?").
 */

type Korinish = "jadval" | "kartochka" | "xarita";

const RANG = {
  yaxshi: "text-yaxshi",
  past: "text-past",
  neytral: "text-matn-past",
} as const;

/** Xarita katakchasining foni.
 *
 * To'yinganlik o'zgarishning KUCHIGA qarab ortadi: kichik
 * tebranishda deyarli rangsiz, katta harakatda to'yingan. Aks holda
 * +0.2% ham, +9% ham bir xil yashil bo'lib ko'rinardi va xarita
 * hech narsa aytmasdi.
 */
function xaritaFoni(foiz: number | null): string {
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

/** Coin belgisi. Logotip kelmasa — tickerning birinchi harfi.
 *
 * Bo'sh joy qoldirilmaydi: qatorlar tekis turishi kerak, aks holda
 * ro'yxat "sinib" ko'rinadi.
 */
function Belgi({ coin, olcham = 22 }: { coin: CoinHolati; olcham?: number }) {
  if (coin.logo === null) {
    return (
      <span
        aria-hidden
        style={{ width: olcham, height: olcham }}
        className="bg-panel-yorqin text-matn-past inline-flex shrink-0 items-center justify-center rounded-full text-[10px] font-semibold"
      >
        {coin.ticker.slice(0, 2)}
      </span>
    );
  }
  return (
    <Image
      src={coin.logo}
      alt=""
      width={olcham}
      height={olcham}
      unoptimized
      className="shrink-0 rounded-full"
    />
  );
}

/** Foiz — uchburchak belgisi bilan.
 *
 * Faqat rang emas, SHAKL ham farq qiladi: rang ajrata olmaydigan
 * odam ham o'sish va tushishni ko'radi.
 */
function Foiz({ qiymat, yirik }: { qiymat: number | null; yirik?: boolean }) {
  if (qiymat === null) return <span className="text-matn-past">—</span>;
  const rol = foizRangi(qiymat);
  const belgi = rol === "yaxshi" ? "▲" : rol === "past" ? "▼" : "•";
  return (
    <span
      className={cn("raqam whitespace-nowrap", RANG[rol], yirik && "text-base")}
    >
      <span aria-hidden className="mr-0.5 text-[9px]">
        {belgi}
      </span>
      {Math.abs(qiymat).toFixed(2)}%
    </span>
  );
}

function MiniGrafik({
  qiymatlar,
  foiz,
  eni = 104,
  boyi = 32,
}: {
  qiymatlar: number[];
  foiz: number | null;
  eni?: number;
  boyi?: number;
}) {
  const chiziq = chiziqNuqtalari(qiymatlar, eni, boyi);
  const maydon = chiziqMaydoni(qiymatlar, eni, boyi);
  // Ma'lumot yetarli emas — bo'sh joy qoladi. Tekis chiziq chizsak
  // "narx o'zgarmadi" degan MA'LUMOT bo'lardi, aslida bilmaymiz.
  if (chiziq === null || maydon === null) {
    return <span className="text-matn-past text-xs">—</span>;
  }

  const rol = foizRangi(foiz);
  const rang =
    rol === "yaxshi"
      ? "var(--rang-yaxshi)"
      : rol === "past"
        ? "var(--rang-past)"
        : "var(--rang-matn-past)";
  const id = `grad-${rol}`;

  return (
    <svg viewBox={`0 0 ${eni} ${boyi}`} width={eni} height={boyi} aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={rang} stopOpacity="0.35" />
          <stop offset="100%" stopColor={rang} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={maydon} fill={`url(#${id})`} />
      <polyline
        points={chiziq}
        fill="none"
        stroke={rang}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
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
  qidir: string;
  topilmadi: string;
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
  const [qidiruv, setQidiruv] = useState("");

  const tartibli = useMemo(() => {
    const izlangan = qidiruv.trim().toLowerCase();
    const tanlangan =
      izlangan === ""
        ? coinlar
        : coinlar.filter(
            (c) =>
              c.ticker.toLowerCase().includes(izlangan) ||
              c.nom.toLowerCase().includes(izlangan),
          );
    return sarala(tanlangan, kalit, osib);
  }, [coinlar, kalit, osib, qidiruv]);

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
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div
          role="tablist"
          aria-label={yorliq.coin}
          className="border-ramka-yumshoq rounded-kichik inline-flex gap-0.5 border p-0.5"
        >
          {tugmalar.map((t) => (
            <button
              key={t.kod}
              type="button"
              role="tab"
              aria-selected={korinish === t.kod}
              onClick={() => setKorinish(t.kod)}
              className={cn(
                "rounded-kichik px-3 py-1.5 text-[13px] transition-colors",
                korinish === t.kod
                  ? "bg-panel-yorqin text-sarlavha font-semibold"
                  : "text-matn-past hover:text-matn",
              )}
            >
              {t.matn}
            </button>
          ))}
        </div>

        <input
          type="search"
          value={qidiruv}
          onChange={(e) => setQidiruv(e.target.value)}
          placeholder={yorliq.qidir}
          aria-label={yorliq.qidir}
          className="border-ramka-yumshoq rounded-kichik bg-panel placeholder:text-matn-past focus:border-ramka w-full max-w-[15rem] border px-3 py-1.5 text-[13px] outline-none"
        />
      </div>

      {tartibli.length === 0 ? (
        <p className="text-matn-past py-8 text-center text-sm">
          {yorliq.topilmadi}
        </p>
      ) : korinish === "jadval" ? (
        <Jadval
          coinlar={tartibli}
          kalit={kalit}
          osib={osib}
          ustunBos={ustunBos}
          yorliq={yorliq}
        />
      ) : korinish === "kartochka" ? (
        <Kartochkalar coinlar={tartibli} yorliq={yorliq} />
      ) : (
        <Xarita coinlar={tartibli} />
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
    // Jadval TOR ekranga sig'maydi va sig'dirishga urinish uni o'qib
    // bo'lmas holga keltiradi. Shuning uchun O'ZI siljiydi — sahifa
    // yon tomonga surilmaydi.
    <div className="-mx-4 overflow-x-auto sm:mx-0">
      <table className="w-full min-w-[52rem] text-[13px]">
        <thead className="text-matn-past border-b border-white/10 text-left text-[11px] tracking-wide uppercase">
          <tr>
            <th scope="col" className="w-10 px-3 py-2 text-right font-medium">
              #
            </th>
            <th scope="col" className="px-2 py-2 font-medium">
              {yorliq.coin}
            </th>
            {ustunlar.map((u) => (
              // `aria-sort` ustun sarlavhasiga tegishli, tugmaga emas:
              // ekran o'quvchi saralashni shu yerdan o'qiydi.
              <th
                key={u.kod}
                scope="col"
                aria-sort={
                  kalit === u.kod ? (osib ? "ascending" : "descending") : "none"
                }
                className="px-3 py-2 text-right font-medium"
              >
                <button
                  type="button"
                  onClick={() => ustunBos(u.kod)}
                  className={cn(
                    "hover:text-matn whitespace-nowrap transition-colors",
                    kalit === u.kod && "text-sarlavha font-semibold",
                  )}
                >
                  {kalit === u.kod && (osib ? "↑ " : "↓ ")}
                  {u.matn}
                </button>
              </th>
            ))}
            <th scope="col" className="px-3 py-2 text-right font-medium">
              {yorliq.yetti_kun}
            </th>
          </tr>
        </thead>
        <tbody>
          {coinlar.map((c, i) => (
            <tr
              key={c.ticker}
              className="hover:bg-panel-yorqin border-b border-white/5 transition-colors last:border-0"
            >
              <td className="raqam text-matn-past px-3 py-2.5 text-right">
                {i + 1}
              </td>
              <th scope="row" className="px-2 py-2.5 text-left font-normal">
                <span className="flex items-center gap-2">
                  <Belgi coin={c} />
                  <span className="text-sarlavha font-semibold">{c.ticker}</span>
                  <span className="text-matn-past hidden truncate text-xs sm:inline">
                    {c.nom}
                  </span>
                </span>
              </th>
              <td className="raqam px-3 py-2.5 text-right whitespace-nowrap">
                {narxMatn(c.narx)}
              </td>
              <td className="px-3 py-2.5 text-right">
                <Foiz qiymat={c.ozgarish24} />
              </td>
              <td className="px-3 py-2.5 text-right">
                <Foiz qiymat={c.ozgarish7k} />
              </td>
              <td className="raqam px-3 py-2.5 text-right whitespace-nowrap">
                {c.kapital === null ? "—" : `$${qisqaSon(c.kapital)}`}
              </td>
              <td className="raqam px-3 py-2.5 text-right whitespace-nowrap">
                {c.hajm24 === null ? "—" : `$${qisqaSon(c.hajm24)}`}
              </td>
              <td className="px-3 py-2.5">
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
    <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
      {coinlar.map((c) => (
        <div
          key={c.ticker}
          className="rounded-kartochka hover:border-ramka border border-white/10 bg-white/[0.02] p-3.5 transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <Belgi coin={c} olcham={30} />
            <div className="min-w-0 flex-1">
              <p className="text-sarlavha leading-tight font-semibold">
                {c.ticker}
              </p>
              <p className="text-matn-past truncate text-xs">{c.nom}</p>
            </div>
            <Foiz qiymat={c.ozgarish24} />
          </div>

          <div className="mt-3 flex items-end justify-between gap-2">
            <p className="raqam text-lg leading-none">{narxMatn(c.narx)}</p>
            <MiniGrafik
              qiymatlar={c.chiziq}
              foiz={c.ozgarish7k}
              eni={92}
              boyi={30}
            />
          </div>

          <dl className="mt-3 flex justify-between gap-2 border-t border-white/5 pt-2.5 text-xs">
            <div>
              <dt className="text-matn-past">{yorliq.kapital}</dt>
              <dd className="raqam mt-0.5">
                {c.kapital === null ? "—" : `$${qisqaSon(c.kapital)}`}
              </dd>
            </div>
            <div className="text-right">
              <dt className="text-matn-past">{yorliq.ozgarish7k}</dt>
              <dd className="mt-0.5">
                <Foiz qiymat={c.ozgarish7k} />
              </dd>
            </div>
          </dl>
        </div>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------- //
//  3. Issiqlik xaritasi
// --------------------------------------------------------------------- //

function Xarita({ coinlar }: { coinlar: CoinHolati[] }) {
  const kataklar = treemap(
    coinlar.map((c) => ({ kalit: c.ticker, ogirlik: c.kapital ?? 0 })),
  );
  const boyicha = new Map(coinlar.map((c) => [c.ticker, c]));

  if (kataklar.length === 0) return null;

  return (
    // Balandlik BELGILANGAN: treemap foizda ishlaydi, ya'ni idishning
    // o'lchami bo'lishi shart. Telefonda pastroq, kengroq ekranda
    // balandroq — kataklar juda yassi bo'lib qolmasin.
    <div className="relative h-[26rem] w-full sm:h-[32rem]">
      {kataklar.map((k) => {
        const coin = boyicha.get(k.kalit);
        if (!coin) return null;
        // Juda kichik katakda matn sig'maydi va o'qilmaydi — faqat
        // ticker qoladi, foiz esa yashiriladi.
        const torgina = k.en < 7 || k.boy < 9;
        return (
          <div
            key={k.kalit}
            title={`${coin.nom} · ${narxMatn(coin.narx)}`}
            style={{
              left: `${k.x}%`,
              top: `${k.y}%`,
              width: `${k.en}%`,
              height: `${k.boy}%`,
              background: xaritaFoni(coin.ozgarish24),
            }}
            className="rounded-kichik absolute flex flex-col items-center justify-center overflow-hidden border border-white/10 p-1 text-center"
          >
            <span className="text-sarlavha text-[11px] leading-tight font-semibold sm:text-xs">
              {k.kalit}
            </span>
            {!torgina && (
              <span className="raqam mt-0.5 text-[10px] leading-tight sm:text-[11px]">
                {coin.ozgarish24 === null
                  ? "—"
                  : `${coin.ozgarish24 > 0 ? "+" : ""}${coin.ozgarish24.toFixed(1)}%`}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
