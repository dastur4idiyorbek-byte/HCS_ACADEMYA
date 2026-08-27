import Image from "next/image";

import { cn } from "@/lib/cn";

/** Logotip + nom. `faqatBelgi` — tor joylar (mobil sarlavha) uchun. */
export function Logo({
  size = 36,
  faqatBelgi = false,
  className,
}: {
  size?: number;
  faqatBelgi?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Image
        src="/logo.jpg"
        alt="HCS — Halol Crypto Savdo"
        width={size}
        height={size}
        className="rounded-kichik"
        priority
      />
      {!faqatBelgi && (
        <span className="leading-tight">
          <span className="text-sarlavha block text-sm font-bold tracking-wide">
            HALOL CRYPTO
          </span>
          <span className="text-matn-past block text-[11px] tracking-[0.2em] uppercase">
            Savdo
          </span>
        </span>
      )}
    </span>
  );
}
