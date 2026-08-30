"use client";

import { useEffect, useState } from "react";

import { kechQoldimi, uzoqlashish } from "@/lib/kirish-holati";

/** Kech kirish ogohlantirishi — HALI KIRMAGAN foydalanuvchi uchun.
 *
 * Signal berilgan paytdagi nisbat (TP masofasi / Stop masofasi) —
 * signalning butun asosi. Narx kirish nuqtasidan uzoqlashgach o'sha
 * nisbat buziladi: yuqoriga ketsa TPgacha masofa qisqaradi va Stop
 * uzoqlashadi, pastga ketsa Stop yaqinlashadi. Ikkalasida ham kirish
 * signal berilgan paytdagidan yomonroq.
 *
 * Tajribali odam buni o'zi hisoblaydi. Yangi foydalanuvchi esa
 * "signal bor ekan" deb kiraveradi — ogohlantirish aynan shu uchun.
 *
 * SIGNALGA ALLAQACHON KIRGAN odamga ko'rsatilmaydi: uning kirish
 * narxi allaqachon belgilangan, bu ogohlantirish unga tegishli emas.
 */
export function KirishOgohlantirish({
  juftlik,
  kirish,
  chegara,
  matnlar,
}: {
  juftlik: string;
  kirish: number;
  /** Necha foizdan keyin ogohlantiriladi (`trade_rules.late_entry_warn_pct`) */
  chegara: number;
  matnlar: { sarlavha: string; izoh: string; masofa: string };
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
        // Narx olinmasa ogohlantirish ham ko'rsatilmaydi — noaniqlikda
        // jim turamiz, yolg'on xotirjamlik ham bermaymiz.
      }
    };

    void yangila();
    const taymer = setInterval(yangila, 20_000);
    return () => {
      tirik = false;
      clearInterval(taymer);
    };
  }, [juftlik]);

  if (!kechQoldimi(kirish, narx, chegara)) return null;

  const masofa = narx === null ? null : uzoqlashish(kirish, narx);
  const yonalish = narx !== null && narx > kirish ? "↑" : "↓";

  return (
    <div className="border-past/60 bg-past/10 rounded-kartochka border p-4">
      <p className="text-past text-sm font-semibold">⚠️ {matnlar.sarlavha}</p>
      <p className="text-matn-past mt-1 text-sm leading-relaxed">{matnlar.izoh}</p>
      {masofa !== null && (
        <p className="raqam text-matn-past mt-2 text-xs">
          {matnlar.masofa}: {yonalish} {masofa.toFixed(2)}%
        </p>
      )}
    </div>
  );
}
