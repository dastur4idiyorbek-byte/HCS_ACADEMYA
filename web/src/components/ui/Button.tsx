import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Variant = "asosiy" | "ikkilamchi" | "shaffof";

const USLUBLAR: Record<Variant, string> = {
  /* Asosiy amal — logotipning apelsin rangi to'liq fon sifatida.
     Matn to'q ko'k: apelsin ustida oq matn kontrasti yetarli emas. */
  asosiy: "bg-ramka text-[#0a2450] hover:brightness-110",
  /* Ikkilamchi — kartochka bilan bir tildagi ramka + turkuaz matn */
  ikkilamchi: "border border-ramka text-sarlavha hover:bg-panel-yorqin",
  shaffof: "text-matn-past hover:text-sarlavha",
};

/* O'chirilgan tugma variantidan QAT'I NAZAR bir xil ko'rinadi.
   Nima uchun `opacity-50` emas: apelsin fonni yarim shaffof qilsak, u to'q
   ko'k bilan aralashib JIGARRANG bo'ladi — bu logotipda yo'q rang va
   "vaqtincha o'chiq" emas, "buzuq" degan taassurot qoldiradi. */
const OCHIRILGAN =
  "border border-matn-past/30 bg-transparent text-matn-past cursor-not-allowed";

type Props = {
  children: ReactNode;
  variant?: Variant;
  href?: string;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  className?: string;
};

/** Tugma yoki havola — ko'rinishi bir xil.
 *
 * `href` berilsa `next/link` bo'ladi: "To'lov qilish" kabi tugmalar
 * aslida boshqa sahifaga (yoki Telegram botga) OLIB BORADI, ular
 * `<button>` bo'lmasligi kerak — skrinreader va "yangi oynada ochish"
 * shunda to'g'ri ishlaydi.
 */
export function Button({
  children,
  variant = "asosiy",
  href,
  onClick,
  type = "button",
  disabled,
  className,
}: Props) {
  const asos = cn(
    "inline-flex items-center justify-center gap-2 rounded-tugma px-4 py-2.5",
    "text-sm font-semibold transition",
    disabled ? OCHIRILGAN : USLUBLAR[variant],
    className,
  );

  if (href && !disabled) {
    const tashqi = href.startsWith("http") || href.startsWith("tg:");
    if (tashqi) {
      return (
        <a className={asos} href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    }
    return (
      <Link className={asos} href={href}>
        {children}
      </Link>
    );
  }

  return (
    <button className={asos} type={type} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}
