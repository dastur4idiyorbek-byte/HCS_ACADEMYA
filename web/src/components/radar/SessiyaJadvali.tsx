import { cn } from "@/lib/cn";
import { type JadvalKatak, type JadvalQatori, type Ustun, ishoraliFoiz } from "@/lib/radar";

import { type Tarjimon, ustunYorligi } from "./matn";

/** Sessiya jadvali (10-bo'lim): har coin — qator, har rasmiy sessiya — ustun.
 *
 * Katak: "#4  −6%" — o'rin va oldingi rasmiy sessiyadan beri narx
 * o'zgarishi. "chiqdi +2%" — oldingi sessiyada o'rin olgan, endi
 * pooldan tushgan coin (uning narxi baribir yoziladi). "—" — bu
 * sessiyada ro'yxatda yo'q.
 *
 * Birinchi ustun (coin nomi) chapga yopishgan: telefonda jadval
 * surilganda ham qaysi qator kimniki ekani ko'rinib turadi. Surish
 * faqat jadval o'ramida — sahifa gorizontal surilmaydi.
 */
export function SessiyaJadvali({
  qatorlar,
  ustunlar,
  zona,
  t,
  sanaKerak,
}: {
  qatorlar: JadvalQatori[];
  ustunlar: Ustun[];
  zona: string;
  t: Tarjimon;
  sanaKerak: boolean;
}) {
  if (qatorlar.length === 0 || ustunlar.length === 0) {
    return <p className="text-matn-past text-sm">{t("radar.jadval_bosh")}</p>;
  }
  return (
    <div className="rounded-kichik border-ramka-yumshoq/60 overflow-x-auto border">
      <table className="raqam w-max min-w-full border-collapse text-xs">
        <thead>
          <tr>
            <th
              scope="col"
              className="bg-panel text-matn-past border-ramka-yumshoq/60 sticky left-0 z-10 border-b px-3 py-2 text-left font-semibold"
            >
              {t("radar.jadval_coin")}
            </th>
            {ustunlar.map((u) => {
              const y = ustunYorligi(t, u, zona, sanaKerak);
              const otkazildi = u.holat === "otkazildi";
              return (
                <th
                  key={u.kalit}
                  scope="col"
                  className="border-ramka-yumshoq/60 border-b px-3 py-2 text-left font-semibold whitespace-nowrap"
                >
                  {y.ustki ? (
                    <span className="text-matn-past block text-[10px] font-normal">{y.ustki}</span>
                  ) : null}
                  <span className={otkazildi ? "text-matn-past" : "text-matn"}>{y.asosiy}</span>
                  {otkazildi ? (
                    <span className="text-past block text-[10px] font-normal">
                      {t("radar.otkazildi")}
                    </span>
                  ) : null}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {qatorlar.map((q) => (
            <tr key={q.symbol} className="border-ramka-yumshoq/30 border-b last:border-b-0">
              <th
                scope="row"
                className="bg-panel text-sarlavha sticky left-0 z-10 px-3 py-1.5 text-left font-semibold whitespace-nowrap"
              >
                {q.belgi || q.symbol}
              </th>
              {q.kataklar.map((k, i) => (
                <td key={ustunlar[i].kalit} className="px-3 py-1.5 whitespace-nowrap">
                  <Katak katak={k} t={t} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Foiz({ foiz }: { foiz: number | null }) {
  if (foiz === null) return <span className="text-matn-past">—</span>;
  const yaxlit = Number(foiz.toFixed(1));
  return (
    <span className={cn(yaxlit > 0 ? "text-yaxshi" : yaxlit < 0 ? "text-past" : "text-matn-past")}>
      {ishoraliFoiz(foiz, Math.abs(foiz) >= 10 ? 0 : 1)}
    </span>
  );
}

function Katak({ katak, t }: { katak: JadvalKatak; t: Tarjimon }) {
  switch (katak.tur) {
    case "otkazildi":
      return <span className="text-matn-past opacity-60">·</span>;
    case "yoq":
      return <span className="text-matn-past">—</span>;
    case "chiqdi":
      return (
        <span className="inline-flex items-baseline gap-2">
          <span className="text-matn-past">{t("radar.chiqdi")}</span>
          <Foiz foiz={katak.foiz} />
        </span>
      );
    case "orinsiz":
      return (
        <span className="inline-flex items-baseline gap-2">
          <span className="text-matn-past">{t("radar.jadval_yashirin")}</span>
          <Foiz foiz={katak.foiz} />
        </span>
      );
    case "orin":
      return (
        <span className="inline-flex items-baseline gap-2">
          <span className="text-matn w-7 font-semibold">#{katak.orin}</span>
          <Foiz foiz={katak.foiz} />
          {katak.tasdiqlangan ? (
            <abbr
              title={t("radar.jadval_tasdiq_izoh")}
              className="border-yaxshi/60 text-yaxshi rounded-[4px] border px-1 text-[10px] leading-4 no-underline"
            >
              {t("radar.jadval_tasdiq")}
            </abbr>
          ) : null}
        </span>
      );
  }
}
