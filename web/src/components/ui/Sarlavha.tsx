import type { ReactNode } from "react";

import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";

/** Sahifa sarlavhasi — hamma bo'limda bir xil ko'rinish.
 *
 * IKONKA sarlavhaning O'ZIDA turadi, matn ichida emas. Ilgari u
 * `matn={`🎬 ${...}`}` ko'rinishida yozilardi va shu sababli:
 *   - tarjima qilinadigan matnga aralashib ketardi;
 *   - brauzer sarlavhasida ham, izlash natijasida ham chiqardi;
 *   - o'lchamini boshqarib bo'lmasdi.
 *
 * Ixtiyoriy: sarlavhasi shaxsiy bo'lgan sahifalarda (masalan bitta
 * maqola) ikonka bermaslik to'g'ri.
 */
export function Sarlavha({
  matn,
  izoh,
  ong,
  belgi,
}: {
  matn: string;
  izoh?: string;
  ong?: ReactNode;
  belgi?: IkonkaNomi;
}) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-sarlavha flex items-center gap-2.5 text-xl font-bold sm:text-2xl">
          {belgi && <Ikonka nom={belgi} className="text-ramka h-6 w-6" />}
          {matn}
        </h1>
        {izoh && (
          <p className="text-matn-past mt-1 max-w-2xl text-sm">{izoh}</p>
        )}
      </div>
      {ong}
    </header>
  );
}
