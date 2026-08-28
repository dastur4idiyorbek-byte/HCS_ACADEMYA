"use client";

import { useEffect, useState } from "react";

import { ozgarishFoizi } from "@/lib/jonli";

/** Signal kirish nuqtasidan narx qancha yurgani — jonli.
 *
 * NIMA UCHUN KERAK: ro'yxatda signal "Faol" deb turadi-yu, u
 * foydaga ketayotganini yoki zarar tomon yurayotganini ko'rsatmasdi.
 * Yangi foydalanuvchi uchun aynan shu birinchi savol.
 *
 * Narx BIZNING serverimizdan olinadi (`/api/narx`), Binance'dan
 * to'g'ridan-to'g'ri emas — sabab `lib/jonli.ts` da.
 *
 * Narx olinmasa HECH NARSA ko'rsatilmaydi: "0.00%" deb yozish
 * yolg'on bo'lardi — u "narx o'zgarmadi" degan ma'noni beradi,
 * aslida esa narx umuman noma'lum.
 */
export function JonliNarx({
  juftlik,
  kirish,
  qisqa = false,
}: {
  /** Birja juftligi — `DOTUSDT` */
  juftlik: string;
  /** Signalning kirish narxi */
  kirish: number;
  /** Qisqa ko'rinish — faqat foiz (ro'yxat uchun) */
  qisqa?: boolean;
}) {
  const [narx, setNarx] = useState<number | null>(null);

  useEffect(() => {
    let tirik = true;

    const yangila = async () => {
      try {
        const javob = await fetch(`/api/narx?juftlar=${encodeURIComponent(juftlik)}`);
        if (!javob.ok) return;
        const natija = (await javob.json()) as { narxlar?: Record<string, number> };
        const qiymat = natija.narxlar?.[juftlik.toUpperCase()];
        if (tirik && typeof qiymat === "number") setNarx(qiymat);
      } catch {
        // Tarmoq uzilsa oxirgi ma'lum narx qoladi — sahifa buzilmaydi.
      }
    };

    void yangila();
    // 20 soniya: narx jonli his qilinsin, lekin telefon batareyasi va
    // Binance chegarasi ham ayanmasin.
    const taymer = setInterval(yangila, 20_000);
    return () => {
      tirik = false;
      clearInterval(taymer);
    };
  }, [juftlik]);

  const foiz = narx === null ? null : ozgarishFoizi(kirish, narx);
  if (foiz === null) return null;

  const musbat = foiz >= 0;
  const rang = musbat ? "text-yaxshi" : "text-past";
  const matn = `${musbat ? "+" : "−"}${Math.abs(foiz).toFixed(2)}%`;

  if (qisqa) {
    return <span className={`raqam text-xs font-semibold ${rang}`}>{matn}</span>;
  }
  return (
    <span className={`raqam font-semibold ${rang}`}>
      {narx === null ? "" : narx.toLocaleString("en-US", { maximumFractionDigits: 8 })}{" "}
      <span className="text-xs">({matn})</span>
    </span>
  );
}
