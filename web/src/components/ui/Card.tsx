import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type CardProps = {
  children: ReactNode;
  /** `urgu` — muhim kartochka: ramka to'liq apelsin rangida.
   *  `oyna` — shisha yuza: urg'u ramkasi + orqadagi fon nuri
   *  xiralashadi (`globals.css` dagi `.oyna-yuza`). */
  variant?: "oddiy" | "urgu" | "oyna";
  className?: string;
};

/** Dizayn tizimining asosiy g'ishti.
 *
 * Topshiriqning 1-bo'limi: har bir kartochka fondan ajralib turadigan
 * INGICHKA chiziq bilan o'ralgan, chiziq — logotipdagi "C" (apelsin)
 * rangida, burchak esa sal yumaloqlashgan (14px).
 *
 * Oddiy kartochkada ramka shaffofroq: ekranda o'nlab kartochka bo'lsa,
 * hammasi to'liq apelsin bo'lib turishi ko'zni charchatadi — urg'u esa
 * urg'u bo'lib qolmaydi.
 *
 * `oyna` ham xuddi shu sababdan SANOQLI joyda ishlatiladi. Ikkinchi
 * sabab texnik: `backdrop-filter` orqadagi hamma narsani qayta
 * chizadi va bir ekranda o'nlab shisha yuza kuchsiz telefonni
 * sekinlashtiradi.
 */
export function Card({ children, variant = "oddiy", className }: CardProps) {
  const oyna = variant === "oyna";
  return (
    <div
      className={cn(
        "rounded-kartochka border p-4 sm:p-5",
        oyna ? "oyna-yuza" : "bg-panel",
        variant === "oddiy" ? "border-ramka-yumshoq" : "border-ramka",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardTitle({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <h2
      className={cn(
        "text-sarlavha text-base font-semibold sm:text-lg",
        className,
      )}
    >
      {children}
    </h2>
  );
}

export function CardHint({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p className={cn("text-matn-past mt-1 text-sm", className)}>{children}</p>
  );
}
