import type { ReactNode } from "react";

/** Sahifa sarlavhasi — hamma bo'limda bir xil ko'rinish. */
export function Sarlavha({
  matn,
  izoh,
  ong,
}: {
  matn: string;
  izoh?: string;
  ong?: ReactNode;
}) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-sarlavha text-xl font-bold sm:text-2xl">{matn}</h1>
        {izoh && (
          <p className="text-matn-past mt-1 max-w-2xl text-sm">{izoh}</p>
        )}
      </div>
      {ong}
    </header>
  );
}
