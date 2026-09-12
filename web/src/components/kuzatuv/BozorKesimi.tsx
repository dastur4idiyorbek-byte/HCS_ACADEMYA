import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import {
  type KuzatuvBozori,
  likvidlik,
  muomalaUlushi,
  sutkalikOrin,
} from "@/lib/kuzatuv";

/** CoinGecko ning ASOSIY ma'lumotlari — bitta joyda.
 *
 * IKKI SAHIFADA ISHLATILADI: admin chuqur ko'rinishi va
 * foydalanuvchi qidiruvi. Ikki nusxa qilinsa, yangi ko'rsatkich
 * qo'shilganda biri yangilanib ikkinchisi qolib ketardi — bu
 * loyihada allaqachon uchragan xato turi.
 *
 * `toliq` — admin uchun: ta'minot, FDV va tarixiy chekkalar ham
 * chiqadi. Foydalanuvchiga asosiy qatorlar yetarli.
 *
 * QAT'IY CHEGARA: bu yerda Entry, Stop yoki TP yo'q. Barcha
 * raqamlar — bozor holati, tavsiya emas.
 */
export function BozorKesimi({
  bozor,
  t,
  toliq = false,
}: {
  bozor: KuzatuvBozori;
  t: (kalit: string) => string;
  toliq?: boolean;
}) {
  const likv = likvidlik(bozor);
  const ulush = muomalaUlushi(bozor);
  const kunOrni = sutkalikOrin(bozor.narx, bozor.past24s, bozor.yuqori24s);

  return (
    <Card className="mb-3">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sarlavha text-lg font-semibold tabular-nums">
          {narx(bozor.narx) ?? "—"}
        </p>
        {bozor.orinCg !== null ? (
          <span className="border-ramka-yumshoq text-matn-past rounded-full border px-2 py-0.5 text-xs">
            {t("kuzatuv.orin")} #{bozor.orinCg}
          </span>
        ) : null}
      </div>

      {/* Narx o'zgarishi — uch oraliq */}
      <div className="border-ramka-yumshoq mb-3 grid grid-cols-3 gap-3 border-b pb-3 text-sm">
        <Qator nom={t("kuzatuv.soat_1")} qiymat={foiz(bozor.ozgarish1s)} ranglash />
        <Qator nom={t("kuzatuv.soat_24")} qiymat={foiz(bozor.ozgarish24s)} ranglash />
        <Qator nom={t("kuzatuv.kun_7")} qiymat={foiz(bozor.ozgarish7k)} ranglash />
      </div>

      {/* Sutkalik oraliq — narx kun ichida qayerda */}
      {kunOrni !== null ? (
        <div className="mb-3">
          <div className="text-matn-past mb-1 flex justify-between text-[11px] tabular-nums">
            <span>{narx(bozor.past24s)}</span>
            <span>{t("kuzatuv.sutka_oraliq")}</span>
            <span>{narx(bozor.yuqori24s)}</span>
          </div>
          <div className="bg-panel-yorqin relative h-1.5 overflow-hidden rounded-full">
            <div
              className="bg-sarlavha absolute top-0 h-full w-1 rounded-full"
              style={{ left: `calc(${kunOrni}% - 2px)` }}
            />
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
        <Qator nom={t("kuzatuv.market_cap")} qiymat={pul(bozor.marketCap)} />
        <Qator nom={t("kuzatuv.hajm_24s")} qiymat={pul(bozor.hajm24s)} />
        <Qator
          nom={t("kuzatuv.likvidlik")}
          qiymat={likv === null ? null : `${likv}%`}
          izoh={t("kuzatuv.likvidlik_izoh")}
        />
        {toliq ? (
          <>
            <Qator nom={t("kuzatuv.fdv")} qiymat={pul(bozor.fdv)} />
            <Qator
              nom={t("kuzatuv.muomalada")}
              qiymat={ulush === null ? miqdor(bozor.muomalada) : `${ulush}%`}
              izoh={t("kuzatuv.muomalada_izoh")}
            />
            <Qator
              nom={t("kuzatuv.ath")}
              qiymat={
                bozor.athFarq === null
                  ? narx(bozor.ath)
                  : `${narx(bozor.ath)} (${foiz(bozor.athFarq)})`
              }
            />
          </>
        ) : null}
      </div>
    </Card>
  );
}

function Qator({
  nom,
  qiymat,
  izoh,
  ranglash = false,
}: {
  nom: string;
  qiymat: string | null;
  izoh?: string;
  /** Musbat — yashil, manfiy — qizil */
  ranglash?: boolean;
}) {
  const manfiy = ranglash && qiymat !== null && qiymat.startsWith("-");
  const musbat = ranglash && qiymat !== null && qiymat.startsWith("+");
  return (
    <div>
      <p className="text-matn-past text-[11px]" title={izoh}>
        {nom}
      </p>
      <p
        className={cn(
          "tabular-nums",
          musbat ? "text-yaxshi" : manfiy ? "text-past" : undefined,
        )}
      >
        {qiymat ?? "—"}
      </p>
    </div>
  );
}

/** $1.2B ko'rinishida. `null` — "ma'lumot yo'q", nol EMAS. */
export function pul(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  const birliklar: [number, string][] = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [chegara, belgi] of birliklar) {
    if (Math.abs(x) >= chegara) return `$${(x / chegara).toFixed(2)}${belgi}`;
  }
  return `$${x.toFixed(2)}`;
}

/** Token soni — dollarsiz. */
export function miqdor(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  const birliklar: [number, string][] = [
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [chegara, belgi] of birliklar) {
    if (Math.abs(x) >= chegara) return `${(x / chegara).toFixed(2)}${belgi}`;
  }
  return x.toFixed(0);
}

export function foiz(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  return `${x > 0 ? "+" : ""}${x.toFixed(2)}%`;
}

/** Narx — kichik coinlar uchun ko'proq raqam kerak. */
export function narx(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  if (Math.abs(x) >= 1) return `$${x.toFixed(2)}`;
  return `$${x.toPrecision(4)}`;
}
