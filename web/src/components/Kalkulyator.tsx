"use client";

import { useMemo, useState } from "react";

import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import {
  ULUSH_JAMI,
  asosiyAktiv,
  hisobla,
  musbatSon,
  tengUlushlar,
} from "@/lib/kalkulyator";

/** Trading kalkulyatori — brauzerda, real vaqtda.
 *
 * Backend so'rovi YO'Q: foydalanuvchi summani yoki ulushni o'zgartirsa,
 * natija darhol qayta hisoblanadi. Hisob-kitobning o'zi
 * `lib/kalkulyator.ts` da — u sof funksiya va test bilan qoplangan.
 *
 * TP soni signaldan keladi. Hozircha signalda ikkita TP bor, lekin
 * komponent massiv qabul qiladi: uchinchisi qo'shilsa, bu yerda hech
 * narsa o'zgarmaydi.
 */

type Matnli = { narx: string; ulush: string };

const uslub =
  "border-ramka-yumshoq rounded-tugma bg-fon raqam w-full border px-3 py-2 text-sm";

export function Kalkulyator({
  symbol,
  entry,
  stop,
  tpNarxlari,
  matnlar,
}: {
  symbol: string;
  entry: number;
  stop: number;
  tpNarxlari: number[];
  matnlar: Record<string, string>;
}) {
  const aktiv = asosiyAktiv(symbol);
  const [summa, setSumma] = useState("1000");
  const [kirish, setKirish] = useState(String(entry));
  const [stopMatn, setStopMatn] = useState(String(stop));
  const [tplar, setTplar] = useState<Matnli[]>(() => {
    const ulushlar = tengUlushlar(tpNarxlari.length);
    return tpNarxlari.map((n, i) => ({ narx: String(n), ulush: String(ulushlar[i]) }));
  });

  const hisob = useMemo(() => {
    const s = musbatSon(summa);
    const e = musbatSon(kirish);
    if (s === null || e === null) return null;
    return hisobla(
      s,
      e,
      musbatSon(stopMatn) ?? 0,
      tplar.map((t) => ({
        narx: musbatSon(t.narx) ?? 0,
        ulush: Number(t.ulush.replace(",", ".")) || 0,
      })),
    );
  }, [summa, kirish, stopMatn, tplar]);

  const yangila = (i: number, maydon: keyof Matnli, qiymat: string) =>
    setTplar((oldingi) =>
      oldingi.map((t, j) => (i === j ? { ...t, [maydon]: qiymat } : t)),
    );

  const pul = (x: number) =>
    `${x >= 0 ? "+" : "−"}$${Math.abs(x).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  const foiz = (x: number) => `${x >= 0 ? "+" : ""}${x.toFixed(2)}%`;
  const miqdor = (x: number) => x.toLocaleString("en-US", { maximumFractionDigits: 8 });

  return (
    <Card>
      <CardTitle>🧮 {matnlar.sarlavha}</CardTitle>

      <div className="mt-4 space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="text-matn-past mb-1 block text-xs uppercase">
              {matnlar.summa}
            </span>
            <input
              inputMode="decimal"
              value={summa}
              onChange={(e) => setSumma(e.target.value)}
              className={uslub}
            />
          </label>
          <label className="block">
            <span className="text-matn-past mb-1 block text-xs uppercase">
              {matnlar.kirish}
            </span>
            <input
              inputMode="decimal"
              value={kirish}
              onChange={(e) => setKirish(e.target.value)}
              className={uslub}
            />
          </label>
          <label className="block">
            <span className="text-matn-past mb-1 block text-xs uppercase">
              {matnlar.stop}
            </span>
            <input
              inputMode="decimal"
              value={stopMatn}
              onChange={(e) => setStopMatn(e.target.value)}
              className={uslub}
            />
          </label>
        </div>

        {tplar.map((t, i) => (
          <div key={i} className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-matn-past mb-1 block text-xs uppercase">
                TP{i + 1}
              </span>
              <input
                inputMode="decimal"
                value={t.narx}
                onChange={(e) => yangila(i, "narx", e.target.value)}
                className={uslub}
              />
            </label>
            <label className="block">
              <span className="text-matn-past mb-1 block text-xs uppercase">
                {matnlar.ulush} %
              </span>
              <input
                inputMode="decimal"
                value={t.ulush}
                onChange={(e) => yangila(i, "ulush", e.target.value)}
                className={uslub}
              />
            </label>
          </div>
        ))}
      </div>

      {hisob && !hisob.toliqmi && (
        <p className="border-ortacha/60 text-ortacha rounded-kichik mt-3 border px-3 py-2 text-sm">
          ⚠️ {matnlar.ulush_xato.replace("{jami}", hisob.ulushJami.toFixed(2))}
        </p>
      )}

      {hisob && (
        <div className="border-ramka-yumshoq rounded-kichik mt-4 border p-3">
          <p className="text-matn-past raqam text-xs">
            {matnlar.umumiy}: {miqdor(hisob.umumiyMiqdor)} {aktiv}
          </p>

          <ul className="mt-3 space-y-2">
            {hisob.tplar.map((t, i) => (
              <li key={i} className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                <span>
                  🎯 TP{i + 1}{" "}
                  <span className="text-matn-past raqam text-xs">
                    ({t.ulush}% — {miqdor(t.miqdor)} {aktiv})
                  </span>
                </span>
                <span className="raqam text-yaxshi font-semibold">
                  {pul(t.foyda)}{" "}
                  <span className="text-matn-past text-xs">({foiz(t.foizOzgarish)})</span>
                </span>
              </li>
            ))}

            <li className="flex flex-wrap items-baseline justify-between gap-2 border-t border-white/10 pt-2 text-sm">
              <span>
                🛑 {matnlar.stop_agar}{" "}
                <span className="text-matn-past text-xs">(100%)</span>
              </span>
              <span className="raqam text-past font-semibold">
                {pul(-hisob.stopZarar)}{" "}
                <span className="text-matn-past text-xs">({foiz(hisob.stopFoiz)})</span>
              </span>
            </li>
          </ul>

          <div className="border-ramka/50 mt-3 flex flex-wrap items-baseline justify-between gap-2 border-t pt-3">
            <span className="text-sm font-semibold">💰 {matnlar.jami}</span>
            <span className="raqam text-sarlavha text-lg font-bold">
              {pul(hisob.jamiFoyda)}{" "}
              <span className="text-matn-past text-sm">({foiz(hisob.jamiFoiz)})</span>
            </span>
          </div>
        </div>
      )}

      <CardHint className="mt-3">ℹ️ {matnlar.ogohlantirish}</CardHint>
    </Card>
  );
}

export { ULUSH_JAMI };
