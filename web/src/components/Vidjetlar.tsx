import Link from "next/link";

import { qisqaSon } from "@/lib/bozor";
import { Ikonka } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";
import type { VidjetKod } from "@/lib/vidjetlar";

/** Bitta vidjetga kerak bo'ladigan hamma ma'lumot.
 *
 * NEGA BITTA OBYEKT. Sahifa vidjetlarni RO'YXAT sifatida chizadi va
 * qaysi biri qaysi tartibda turishini oldindan bilmaydi. Har biriga
 * alohida prop uzatilsa, sahifa har bir vidjetni nomi bilan bilishi
 * kerak bo'lardi — u holda foydalanuvchi tartibni o'zgartirganda kod
 * ham o'zgarishi kerak edi.
 */
export type VidjetMalumoti = {
  salomatlik: number | null;
  salomatlikTasnifi: string | null;
  qorquv: { qiymat: number; tasnif: string } | null;
  altcoin: number | null;
  bozorKapitali: number | null;
  bozorOzgarish: number | null;
  oxirgiSignal: { id: number; coin: string; holat: string } | null;
  ochiqPozitsiya: number;
  natijaUsd: number | null;
  tarif: string | null;
  yangiDars: { id: number; nom: string; turi: string } | null;
};

const RANG = {
  yaxshi: "text-yaxshi",
  past: "text-past",
  neytral: "text-matn-past",
} as const;

function rol(foiz: number | null): keyof typeof RANG {
  if (foiz === null) return "neytral";
  if (foiz > 0.1) return "yaxshi";
  if (foiz < -0.1) return "past";
  return "neytral";
}

/** Vidjet qobig'i — hammasi bir xil o'lchamda tursin.
 *
 * Har biri o'z o'lchamini tanlasa, panel tartibsiz ko'rinardi va
 * foydalanuvchi tartibni o'zgartirganda joylashuv "sakrardi".
 */
function Qobiq({
  nom,
  yol,
  children,
}: {
  nom: string;
  yol?: string;
  children: React.ReactNode;
}) {
  const ichi = (
    <>
      <p className="text-matn-past text-[11px] tracking-wide uppercase">
        {nom}
      </p>
      <div className="mt-1.5">{children}</div>
    </>
  );

  const sinf =
    "rounded-kartochka border border-white/10 bg-white/[0.02] p-3.5 min-h-[5.5rem] flex flex-col";

  return yol ? (
    <Link
      href={yol}
      className={cn(sinf, "hover:border-ramka transition-colors")}
    >
      {ichi}
    </Link>
  ) : (
    <div className={sinf}>{ichi}</div>
  );
}

function Katta({ children }: { children: React.ReactNode }) {
  return (
    <p className="raqam text-sarlavha text-xl leading-none font-bold">
      {children}
    </p>
  );
}

function Bosh({ matn }: { matn: string }) {
  return <p className="text-matn-past text-sm">{matn}</p>;
}

export type VidjetYorliqlari = Record<string, string>;

/** Bitta vidjetni chizadi.
 *
 * Noma'lum kod uchun `null`: bazada eski vidjet qolib ketgan bo'lsa,
 * sahifa buzilmasin.
 */
export function Vidjet({
  kod,
  nom,
  malumot,
  qulf,
  yorliq,
}: {
  kod: VidjetKod;
  nom: string;
  malumot: VidjetMalumoti;
  qulf: boolean;
  yorliq: VidjetYorliqlari;
}) {
  // QULFLANGAN VIDJET YASHIRILMAYDI, lekin RAQAMI ko'rsatilmaydi.
  // Nomi qoladi — u nima berishini bilsin; qiymat esa mahsulot.
  if (qulf) {
    return (
      <Qobiq nom={nom} yol="/profil">
        <p className="text-matn-past flex items-center gap-1.5 text-sm">
          <Ikonka nom="qulf" className="h-4 w-4" />
          {yorliq.qulf}
        </p>
      </Qobiq>
    );
  }

  switch (kod) {
    case "salomatlik":
      return (
        <Qobiq nom={nom} yol="/bozor-holati">
          {malumot.salomatlik === null ? (
            <Bosh matn={yorliq.yoq} />
          ) : (
            <>
              <Katta>{malumot.salomatlik}/100</Katta>
              {malumot.salomatlikTasnifi && (
                <p className="text-matn-past mt-1 text-xs">
                  {malumot.salomatlikTasnifi}
                </p>
              )}
            </>
          )}
        </Qobiq>
      );

    case "qorquv":
      return (
        <Qobiq nom={nom} yol="/bozor-holati">
          {malumot.qorquv === null ? (
            <Bosh matn={yorliq.yoq} />
          ) : (
            <>
              <Katta>{malumot.qorquv.qiymat}</Katta>
              <p className="text-matn-past mt-1 text-xs">
                {malumot.qorquv.tasnif}
              </p>
            </>
          )}
        </Qobiq>
      );

    case "altcoin":
      return (
        <Qobiq nom={nom} yol="/bozor-holati">
          {malumot.altcoin === null ? (
            <Bosh matn={yorliq.yoq} />
          ) : (
            <>
              <Katta>{malumot.altcoin}</Katta>
              <p className="text-matn-past mt-1 text-xs">
                {yorliq.halol_manba}
              </p>
            </>
          )}
        </Qobiq>
      );

    case "bozor_kapitali":
      return (
        <Qobiq nom={nom} yol="/bozor-holati">
          {malumot.bozorKapitali === null ? (
            <Bosh matn={yorliq.yoq} />
          ) : (
            <>
              <Katta>${qisqaSon(malumot.bozorKapitali)}</Katta>
              {malumot.bozorOzgarish !== null && (
                <p
                  className={cn(
                    "raqam mt-1 text-xs",
                    RANG[rol(malumot.bozorOzgarish)],
                  )}
                >
                  {malumot.bozorOzgarish > 0 ? "▲" : "▼"}{" "}
                  {Math.abs(malumot.bozorOzgarish).toFixed(2)}%
                </p>
              )}
            </>
          )}
        </Qobiq>
      );

    case "oxirgi_signal":
      return (
        <Qobiq
          nom={nom}
          yol={
            malumot.oxirgiSignal
              ? `/signallar/${malumot.oxirgiSignal.id}`
              : "/signallar"
          }
        >
          {malumot.oxirgiSignal === null ? (
            <Bosh matn={yorliq.signal_yoq} />
          ) : (
            <>
              <Katta>{malumot.oxirgiSignal.coin}</Katta>
              <p className="text-matn-past mt-1 text-xs">
                {malumot.oxirgiSignal.holat}
              </p>
            </>
          )}
        </Qobiq>
      );

    case "pozitsiyalar":
      return (
        <Qobiq nom={nom} yol="/portfel">
          <Katta>{malumot.ochiqPozitsiya}</Katta>
          <p className="text-matn-past mt-1 text-xs">{yorliq.dona}</p>
        </Qobiq>
      );

    case "natija":
      return (
        <Qobiq nom={nom} yol="/portfel">
          {malumot.natijaUsd === null ? (
            // Nol ko'rsatilmaydi: "$0.00" — "hisoblab bo'lmadi" emas,
            // "hech narsa yutmadingiz" degan MA'LUMOT bo'lardi.
            <Bosh matn={yorliq.yoq} />
          ) : (
            <p
              className={cn(
                "raqam text-xl leading-none font-bold",
                RANG[rol(malumot.natijaUsd)],
              )}
            >
              {malumot.natijaUsd > 0 ? "+" : ""}$
              {Math.abs(malumot.natijaUsd).toFixed(2)}
            </p>
          )}
        </Qobiq>
      );

    case "tarif":
      return (
        <Qobiq nom={nom} yol="/profil">
          <Katta>{malumot.tarif ?? yorliq.tarif_yoq}</Katta>
        </Qobiq>
      );

    case "yangi_dars":
      return (
        <Qobiq
          nom={nom}
          yol={
            malumot.yangiDars
              ? malumot.yangiDars.turi === "maqola"
                ? `/bilimlar/${malumot.yangiDars.id}`
                : "/video"
              : "/akademiya"
          }
        >
          {malumot.yangiDars === null ? (
            <Bosh matn={yorliq.yoq} />
          ) : (
            <p className="text-sarlavha text-sm leading-snug font-semibold">
              {malumot.yangiDars.nom}
            </p>
          )}
        </Qobiq>
      );

    default:
      return null;
  }
}
