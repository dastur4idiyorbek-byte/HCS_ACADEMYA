"use client";

import { useEffect, useState } from "react";

import { kechQoldimi, kutilmoqdami, uzoqlashish } from "@/lib/kirish-holati";
import { Ikonka } from "@/components/ui/Ikonka";

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
 *
 * KUTAYOTGAN LIMIT SIGNALGA ham ko'rsatilmaydi (`holat === "pending"`).
 * Narx hali kirish nuqtasiga tushmagan — bu xavf emas, rejaning o'zi.
 * Qoida `kechQoldimi` ichida.
 */
export function KirishOgohlantirish({
  juftlik,
  kirish,
  chegara,
  holat,
  matnlar,
}: {
  juftlik: string;
  kirish: number;
  /** Necha foizdan keyin ogohlantiriladi (`trade_rules.late_entry_warn_pct`) */
  chegara: number;
  /** Signal holati — `pending` bo'lsa ogohlantirish CHIQMAYDI */
  holat: string;
  matnlar: {
    sarlavha: string;
    izoh: string;
    masofa: string;
    kutilmoqda: string;
    kutilmoqda_izoh: string;
    qoldi: string;
  };
}) {
  const [narx, setNarx] = useState<number | null>(null);

  useEffect(() => {
    let tirik = true;

    const yangila = async () => {
      try {
        const javob = await fetch(
          `/api/narx?juftlar=${encodeURIComponent(juftlik)}`,
        );
        if (!javob.ok) return;
        const natija = (await javob.json()) as {
          narxlar?: Record<string, number>;
        };
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

  const masofa = narx === null ? null : uzoqlashish(kirish, narx);

  // KUTAYOTGAN LIMIT — ogohlantirish emas, HOLAT. Bu joyda ilgari
  // "xavf kattalashdi" deb yozilardi, aslida esa narx hali kirish
  // nuqtasiga tushmagan edi. Endi o'sha joy to'g'ri narsani aytadi:
  // qancha qolgani.
  if (kutilmoqdami(holat)) {
    if (masofa === null) return null;
    return (
      <div className="border-ramka-yumshoq bg-panel rounded-kartochka border p-4">
        <p className="text-sarlavha text-sm font-semibold">
          ⏳ {matnlar.kutilmoqda}
        </p>
        <p className="text-matn-past mt-1 text-sm leading-relaxed">
          {matnlar.kutilmoqda_izoh}
        </p>
        <p className="raqam text-matn-past mt-2 text-xs">
          {matnlar.qoldi}: {masofa.toFixed(2)}%
        </p>
      </div>
    );
  }

  if (!kechQoldimi(kirish, narx, chegara, holat)) return null;

  const yonalish = narx !== null && narx > kirish ? "↑" : "↓";

  return (
    <div className="border-past/60 bg-past/10 rounded-kartochka border p-4">
      <p className="text-past text-sm font-semibold">
        <Ikonka nom="ogohlantirish" className="inline h-4 w-4 align-[-3px]" />{" "}
        {matnlar.sarlavha}
      </p>
      <p className="text-matn-past mt-1 text-sm leading-relaxed">
        {matnlar.izoh}
      </p>
      {masofa !== null && (
        <p className="raqam text-matn-past mt-2 text-xs">
          {matnlar.masofa}: {yonalish} {masofa.toFixed(2)}%
        </p>
      )}
    </div>
  );
}
