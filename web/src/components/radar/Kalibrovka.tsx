import type { ReactNode } from "react";

import { Ikonka } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";
import {
  KALIBR_GURUHLARI,
  KAM_NAMUNA,
  type Kalibrovka as KalibrovkaTuri,
  TEKSHIRUV_KODLARI,
  type Ulush,
  ishoraliFoiz,
  shablon,
  sonYoz,
} from "@/lib/radar";

import type { Tarjimon } from "./matn";

/** Calibration — radar o'zini o'lchaydi (11-bo'lim).
 *
 * Bu QAROR uchun emas: faqat chegaralarni dalil bilan to'g'rilash
 * uchun. Shuning uchun har raqam yonida `n` (nechta yozuvdan) turadi
 * — 3 tadan 2 tasi portlagan "67%" va 300 dan 200 tasi bir xil
 * ko'rinmasligi kerak. `n < 30` bo'lsa ochiq ogohlantirish chiqadi.
 */
export function Kalibrovka({
  hisob,
  t,
  portlash24,
  portlash7,
  kunlar,
}: {
  hisob: KalibrovkaTuri;
  t: Tarjimon;
  portlash24: number;
  portlash7: number;
  kunlar: number;
}) {
  const izoh = shablon(t("radar.kalibr_izoh"), {
    a: sonYoz(portlash24, 0),
    b: sonYoz(portlash7, 0),
    k: kunlar,
  });
  if (hisob.jami24 === 0 && hisob.jami7 === 0) {
    return (
      <div className="space-y-2">
        <p className="text-matn-past text-xs">{izoh}</p>
        <p className="text-matn text-sm">{t("radar.kalibr_bosh")}</p>
      </div>
    );
  }
  const kamBor = KALIBR_GURUHLARI.some((g) => hisob.guruhlar[g].kam);

  return (
    <div className="space-y-5">
      <p className="text-matn-past text-xs">{izoh}</p>

      {kamBor ? (
        <p className="border-ortacha/60 text-ortacha rounded-kichik flex items-start gap-2 border px-3 py-2 text-xs">
          <Ikonka nom="ogohlantirish" className="mt-0.5 h-3.5 w-3.5" />
          {shablon(t("radar.kam_ogoh"), { n: KAM_NAMUNA })}
        </p>
      ) : null}

      <Jadval
        sarlavhalar={[
          t("radar.ustun_guruh"),
          t("radar.ustun_portlash24"),
          t("radar.ustun_portlash7"),
          t("radar.ustun_max24"),
          t("radar.ustun_min24"),
        ]}
      >
        {KALIBR_GURUHLARI.map((g) => {
          const q = hisob.guruhlar[g];
          return (
            <tr key={g} className="border-ramka-yumshoq/30 border-b last:border-b-0">
              <th scope="row" className="text-matn px-3 py-1.5 text-left font-medium whitespace-nowrap">
                {t(`radar.guruh.${g}`)}
                {q.kam ? (
                  <Ikonka
                    nom="ogohlantirish"
                    className="text-ortacha ml-1.5 inline h-3.5 w-3.5 align-[-2px]"
                    nomi={shablon(t("radar.kam_ogoh"), { n: KAM_NAMUNA })}
                  />
                ) : null}
              </th>
              <UlushKatak u={q.kun24} />
              <UlushKatak u={q.kun7} />
              <SonKatak x={q.ortachaMax24} />
              <SonKatak x={q.ortachaMin24} />
            </tr>
          );
        })}
      </Jadval>
      <p className="text-matn-past -mt-3 text-[11px]">{t("radar.namuna_izoh")}</p>

      <section>
        <h4 className="text-sarlavha mb-2 text-xs font-semibold">{t("radar.tekshiruv_boyicha")}</h4>
        <Jadval
          sarlavhalar={[
            t("radar.ustun_tekshiruv"),
            t("radar.ustun_ha"),
            t("radar.ustun_yoq"),
            t("radar.ustun_malumot_yoq"),
          ]}
        >
          {TEKSHIRUV_KODLARI.map((kod) => {
            const q = hisob.tekshiruvlar[kod];
            return (
              <tr key={kod} className="border-ramka-yumshoq/30 border-b last:border-b-0">
                <th scope="row" className="text-matn px-3 py-1.5 text-left font-medium whitespace-nowrap">
                  {t(`radar.tek.${kod}`)}
                </th>
                <UlushKatak u={q.ha.kun24} />
                <UlushKatak u={q.yoq.kun24} />
                <td className="text-matn-past px-3 py-1.5">{q.malumotYoq}</td>
              </tr>
            );
          })}
        </Jadval>
      </section>

      <section>
        <h4 className="text-sarlavha mb-2 text-xs font-semibold">{t("radar.soni_boyicha")}</h4>
        <Jadval
          sarlavhalar={[t("radar.ustun_soni"), t("radar.ustun_portlash24"), t("radar.ustun_portlash7")]}
        >
          {hisob.tasdiqSoni.map((q) => (
            <tr key={q.soni} className="border-ramka-yumshoq/30 border-b last:border-b-0">
              <th scope="row" className="text-matn px-3 py-1.5 text-left font-medium">
                {q.soni}/{TEKSHIRUV_KODLARI.length}
              </th>
              <UlushKatak u={q.kun24} />
              <UlushKatak u={q.kun7} />
            </tr>
          ))}
        </Jadval>
      </section>
    </div>
  );
}

function Jadval({ sarlavhalar, children }: { sarlavhalar: string[]; children: ReactNode }) {
  return (
    <div className="rounded-kichik border-ramka-yumshoq/60 overflow-x-auto border">
      <table className="raqam w-full min-w-max border-collapse text-xs">
        <thead>
          <tr>
            {sarlavhalar.map((s) => (
              <th
                key={s}
                scope="col"
                className="text-matn-past border-ramka-yumshoq/60 border-b px-3 py-2 text-left font-semibold whitespace-nowrap"
              >
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

/** Ulush: "23% (7/30)". `n = 0` — "—". Kam namunada xiraroq. */
function UlushKatak({ u }: { u: Ulush }) {
  if (u.ulush === null) return <td className="text-matn-past px-3 py-1.5">—</td>;
  return (
    <td className={cn("px-3 py-1.5 whitespace-nowrap", u.n < KAM_NAMUNA ? "text-matn-past" : "text-matn")}>
      {sonYoz(u.ulush, 0)}%{" "}
      <span className="text-matn-past text-[11px]">
        ({u.portlash}/{u.n})
      </span>
    </td>
  );
}

function SonKatak({ x }: { x: number | null }) {
  return (
    <td className="text-matn px-3 py-1.5 whitespace-nowrap">
      {x === null ? "—" : ishoraliFoiz(x, 1)}
    </td>
  );
}
