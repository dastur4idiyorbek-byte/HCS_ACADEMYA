"use client";

import { useEffect, useRef, useState } from "react";

/** Stakan va savdo lentasi — BRAUZER to'g'ridan-to'g'ri birjadan oladi.
 *
 * NEGA SERVER ORQALI EMAS. Stakan sekundiga o'nlab marta o'zgaradi.
 * Uni serverda ushlab, bazaga yozib, keyin saytga uzatish uch narsani
 * qo'shadi: server yuki, kechikish va yana bitta buziladigan joy.
 * Brauzer esa to'g'ridan-to'g'ri ulansa — serverga NOL yuk va
 * ma'lumot chinakam jonli.
 *
 * XARID BOSIMI VA YIRIK SAVDOLAR BU YERDA EMAS. Ular "so'nggi 15
 * daqiqa" haqida, brauzer esa sahifani endi ochgan va o'tgan 15
 * daqiqani ko'rmagan. Ularni bot uzluksiz yig'adi
 * (`core/watch_panel/live_market_data.py`).
 *
 * ULANISH TAB YOPILGANDA UZILADI. `useEffect` tozalash funksiyasi
 * soketni yopadi — aks holda admin sahifadan chiqqach ham ulanish
 * ochiq qolardi va har ochilishda bittadan to'planardi.
 *
 * QAT'IY CHEGARA: bu yerda Entry, Stop yoki TP yo'q. Faqat bozor
 * holati ko'rsatiladi.
 */

type Daraja = { narx: number; miqdor: number };
type Lenta = { narx: number; miqdor: number; xarid: boolean; vaqt: number };

const STAKAN_CHUQURLIGI = 10;
const LENTA_UZUNLIGI = 20;

export function JonliStakan({
  symbol,
  matnlar,
}: {
  symbol: string;
  matnlar: {
    stakan: string;
    lenta: string;
    xarid: string;
    sotish: string;
    ulanmoqda: string;
    uzildi: string;
    narx: string;
    miqdor: string;
  };
}) {
  const [xaridlar, setXaridlar] = useState<Daraja[]>([]);
  const [sotishlar, setSotishlar] = useState<Daraja[]>([]);
  const [lenta, setLenta] = useState<Lenta[]>([]);
  // SYMBOL MANZILDAN KELADI — ishonchsiz kirish.
  //
  // Uni tekshirmasdan WebSocket manziliga qo'yish ikki narsani
  // buzardi: noto'g'ri belgi `new WebSocket` ni SINXRON yiqitardi
  // (va React effekt ichida sinxron holat o'zgartirishga ruxsat
  // bermaydi), hamda manzilga begona oqim qo'shib yuborish mumkin
  // bo'lardi. Shuning uchun faqat harf va raqam o'tadi.
  const yaroqli = /^[A-Za-z0-9]{1,15}$/.test(symbol);
  const [holat, setHolat] = useState<"ulanmoqda" | "ulandi" | "uzildi">(
    yaroqli ? "ulanmoqda" : "uzildi",
  );
  const lentaRef = useRef<Lenta[]>([]);

  useEffect(() => {
    if (!yaroqli) return;

    const past = symbol.toLowerCase();
    const manzil =
      `wss://stream.binance.com:9443/stream?streams=` +
      `${past}usdt@depth${STAKAN_CHUQURLIGI}@1000ms/${past}usdt@aggTrade`;

    let yopilgan = false;
    const soket = new WebSocket(manzil);

    soket.onopen = () => {
      if (!yopilgan) setHolat("ulandi");
    };
    soket.onerror = () => {
      if (!yopilgan) setHolat("uzildi");
    };
    soket.onclose = () => {
      if (!yopilgan) setHolat("uzildi");
    };

    soket.onmessage = (hodisa) => {
      let paket: { stream?: string; data?: Record<string, unknown> };
      try {
        paket = JSON.parse(hodisa.data as string);
      } catch {
        return;
      }
      const d = paket.data;
      if (!d) return;

      if (paket.stream?.includes("@depth")) {
        setXaridlar(darajalar(d.bids));
        setSotishlar(darajalar(d.asks));
        return;
      }
      if (paket.stream?.includes("@aggTrade")) {
        const narx = Number(d.p);
        const miqdor = Number(d.q);
        if (!Number.isFinite(narx) || !Number.isFinite(miqdor)) return;
        // `m: true` — xaridor MAKER, ya'ni tashabbuskor SOTUVCHI.
        const yangi: Lenta = { narx, miqdor, xarid: !d.m, vaqt: Number(d.T) };
        lentaRef.current = [yangi, ...lentaRef.current].slice(0, LENTA_UZUNLIGI);
        setLenta(lentaRef.current);
      }
    };

    return () => {
      yopilgan = true;
      soket.close();
    };
  }, [symbol, yaroqli]);

  const eng = Math.max(
    ...xaridlar.map((d) => d.miqdor),
    ...sotishlar.map((d) => d.miqdor),
    1,
  );

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="rounded-kartochka border-ramka-yumshoq bg-panel border p-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-semibold">{matnlar.stakan}</p>
          <Holat holat={holat} matnlar={matnlar} />
        </div>
        <div className="space-y-0.5">
          {sotishlar
            .slice()
            .reverse()
            .map((d, i) => (
              <Qator key={`s${i}`} daraja={d} eng={eng} xarid={false} />
            ))}
          <div className="border-ramka-yumshoq my-1 border-t" />
          {xaridlar.map((d, i) => (
            <Qator key={`x${i}`} daraja={d} eng={eng} xarid />
          ))}
        </div>
      </div>

      <div className="rounded-kartochka border-ramka-yumshoq bg-panel border p-3">
        <p className="mb-2 text-sm font-semibold">{matnlar.lenta}</p>
        <div className="space-y-0.5 font-mono text-[11px] tabular-nums">
          {lenta.map((l, i) => (
            <div key={`${l.vaqt}-${i}`} className="flex justify-between gap-2">
              <span className={l.xarid ? "text-yaxshi" : "text-past"}>
                {l.narx.toPrecision(6)}
              </span>
              <span className="text-matn-past">{l.miqdor.toPrecision(4)}</span>
            </div>
          ))}
          {lenta.length === 0 ? (
            <p className="text-matn-past text-xs">—</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Holat({
  holat,
  matnlar,
}: {
  holat: "ulanmoqda" | "ulandi" | "uzildi";
  matnlar: { ulanmoqda: string; uzildi: string };
}) {
  if (holat === "ulandi") return null;
  return (
    <span className={holat === "uzildi" ? "text-past text-xs" : "text-matn-past text-xs"}>
      {holat === "uzildi" ? matnlar.uzildi : matnlar.ulanmoqda}
    </span>
  );
}

/** Gorizontal bar — miqdor qanchalik kattaligini ko'rsatadi. */
function Qator({
  daraja,
  eng,
  xarid,
}: {
  daraja: Daraja;
  eng: number;
  xarid: boolean;
}) {
  const ulush = Math.min(100, (daraja.miqdor / eng) * 100);
  return (
    <div className="relative flex justify-between gap-2 font-mono text-[11px] tabular-nums">
      <span
        aria-hidden
        className={`absolute inset-y-0 right-0 ${xarid ? "bg-yaxshi/15" : "bg-past/15"}`}
        style={{ width: `${ulush}%` }}
      />
      <span className={`relative ${xarid ? "text-yaxshi" : "text-past"}`}>
        {daraja.narx.toPrecision(6)}
      </span>
      <span className="text-matn-past relative">{daraja.miqdor.toPrecision(4)}</span>
    </div>
  );
}

/** Binance `[narx, miqdor]` juftlarini o'qiydi. Buzuq ma'lumot — bo'sh. */
function darajalar(xom: unknown): Daraja[] {
  if (!Array.isArray(xom)) return [];
  return xom
    .map((juft) => {
      if (!Array.isArray(juft)) return null;
      const narx = Number(juft[0]);
      const miqdor = Number(juft[1]);
      if (!Number.isFinite(narx) || !Number.isFinite(miqdor)) return null;
      return { narx, miqdor };
    })
    .filter((d): d is Daraja => d !== null)
    .slice(0, STAKAN_CHUQURLIGI);
}
