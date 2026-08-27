import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type CardProps = {
  children: ReactNode;
  /** `urgu` — muhim kartochka: ramka to'liq apelsin rangida */
  variant?: "oddiy" | "urgu";
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
 */
export function Card({ children, variant = "oddiy", className }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-kartochka border bg-panel p-4 sm:p-5",
        variant === "urgu" ? "border-ramka" : "border-ramka-yumshoq",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <h2 className={cn("text-sarlavha text-base font-semibold sm:text-lg", className)}>
      {children}
    </h2>
  );
}

export function CardHint({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-matn-past mt-1 text-sm", className)}>{children}</p>;
}
