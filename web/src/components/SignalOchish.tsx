"use client";

import { useState } from "react";

import { Grafik } from "@/components/Grafik";
import { Himoya } from "@/components/Himoya";
import { Kalkulyator } from "@/components/Kalkulyator";
import { SignalKartochka } from "@/components/SignalKartochka";
import { birjaJuftligi } from "@/lib/kalkulyator";

/** Signallar RO'YXATIDA grafik va kalkulyatorni ochadigan tugma.
 *
 * NEGA YOPIQ TURADI: har bir TradingView widget'i alohida `iframe` va
 * alohida tashqi skript. Uchta faol signal bo'lsa, sahifa uchta grafikni
 * bir vaqtda yuklardi — telefonda bu sezilarli sekinlashuv. Shuning
 * uchun widget faqat FOYDALANUVCHI OCHGANDA quriladi: yopiq turganda
 * DOM da umuman yo'q.
 *
 * Himoya qatlami bu yerda ham xuddi signal sahifasidagidek taqsimlangan:
 * grafik tashqarida (ochiq bozor ma'lumoti), kalkulyator ichida (uning
 * maydonlarida kirish, Stop va TP narxlari turadi).
 */
export function SignalOchish({
  symbol,
  entry,
  stop,
  tpNarxlari,
  belgi,
  kotirovka,
  tp1Ulush,
  buyurtmaMatni,
  berilgan,
  matnlar,
}: {
  symbol: string;
  entry: number;
  stop: number;
  tpNarxlari: number[];
  belgi: string;
  /** TP1 da sotiladigan ulush — konfiguratsiyadan, serverdan keladi */
  tp1Ulush: number;
  buyurtmaMatni: string;
  berilgan: Date | null;
  /** Spot juftlik kotirovkasi (`USDT`). SERVERDAN keladi: uni
   *  konfiguratsiyadan o'qish fayl tizimini talab qiladi, brauzerda esa
   *  bunday imkoniyat yo'q. */
  kotirovka: string;
  matnlar: Record<string, string>;
}) {
  const [ochiq, setOchiq] = useState(false);

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOchiq((x) => !x)}
        aria-expanded={ochiq}
        className="text-sarlavha hover:bg-panel-yorqin rounded-tugma -mx-2 flex w-full items-center gap-2 px-2 py-1.5 text-sm font-medium transition"
      >
        <span aria-hidden className={ochiq ? "rotate-90 transition" : "transition"}>
          ›
        </span>
        📈 {matnlar.ochish}
      </button>

      {ochiq && (
        <div className="mt-3 space-y-4">
          {/* Tartib: SIGNAL -> grafik -> kalkulyator. Avval kalkulyator
              birinchi ochilardi va qaysi narx signalniki ekani
              bilinmasdi. */}
          <Himoya belgi={belgi} ogohlantirish={matnlar.himoya}>
            <SignalKartochka
              symbol={symbol}
              kotirovka={kotirovka}
              entry={entry}
              stop={stop}
              tp1={tpNarxlari[0]}
              tp2={tpNarxlari[1]}
              tp1Ulush={tp1Ulush}
              buyurtmaMatni={buyurtmaMatni}
              berilgan={berilgan}
              matnlar={matnlar}
            />
          </Himoya>

          <Grafik
            symbol={`BINANCE:${birjaJuftligi(symbol, kotirovka)}`}
            xatoMatni={matnlar.grafik_xato}
          />

          <Himoya belgi={belgi} ogohlantirish={matnlar.himoya}>
            <Kalkulyator
              symbol={symbol}
              kotirovka={kotirovka}
              entry={entry}
              stop={stop}
              tpNarxlari={tpNarxlari}
              matnlar={matnlar}
            />
          </Himoya>
        </div>
      )}
    </div>
  );
}
