import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";
import {
  type HalolHolati,
  type Natija,
  type TekshiruvHolat,
  narxYoz,
  qisqaPul,
  sanoq,
  shablon,
} from "@/lib/radar";

import { type Tarjimon, manbaNomi, sababMatni, xulosaMatni } from "./matn";

/** Halol reestr — SANOQQA KIRMAYDI, faqat yonida turadi (6-bo'lim).
 *
 * "Hali baholanmagan" alohida holat: reestrda yo'q coinni "halol"
 * deb ko'rsatish yolg'on bo'lardi (`verdict_for()` aynan shunday
 * qilardi — shuning uchun modul reestrni o'zi o'qiydi).
 */
const HALOL_TON: Record<HalolHolati, BadgeTone> = {
  halol: "yaxshi",
  harom: "past",
  shubhali: "ortacha",
  baholanmagan: "neytral",
};
const HALOL_IKONKA: Record<HalolHolati, IkonkaNomi> = {
  halol: "faol",
  harom: "bekor",
  shubhali: "ogohlantirish",
  baholanmagan: "malumot",
};

/** Tekshiruv belgisi — `Segmentlar` dagi bilan BIR XIL shakl.
 *
 * Emoji EMAS (`ui/Ikonka.tsx` dagi qoida): to'ldirilgan kvadrat —
 * tasdiqlandi, qizil kontur — tasdiqlanmadi, deyarli ko'rinmas —
 * o'lchanmadi. Rang yolg'iz qolmaydi: ekran o'qigich uchun matn bor.
 */
export function TekshiruvBelgisi({
  holat,
  t,
  className,
}: {
  holat: TekshiruvHolat;
  t: Tarjimon;
  className?: string;
}) {
  return (
    <span
      role="img"
      aria-label={t(`radar.holat_${holat}`)}
      title={t(`radar.holat_${holat}`)}
      className={cn(
        "inline-block h-3 w-3 shrink-0 rounded-[3px] border",
        holat === "ha"
          ? "border-yaxshi bg-yaxshi"
          : holat === "yoq"
            ? "border-past/60"
            : "border-ramka-yumshoq opacity-40",
        className,
      )}
    />
  );
}

/** Joriy natijadagi bitta coin (7-bo'lim).
 *
 * Tepada — sanoq: "5/7 · Harakat 3/3 · Yoqilg'i 2/4". Ball yoki
 * formula YO'Q: faqat nechta tekshiruv o'tgani.
 *
 * NARX — "o'sha sessiyadagi narx". U kirish uchun tavsiya emas va
 * shunday nomlanmaydi: modul signal bermaydi.
 *
 * Tafsilot `<details>` ichida: ro'yxatda o'nlab coin bo'lishi
 * mumkin, har birining 7 qatori ochiq tursa sahifa o'qib bo'lmas
 * darajada uzayadi. JavaScript kerak emas.
 */
export function NomzodKartochka({
  natija,
  t,
  ochiq = false,
}: {
  natija: Natija;
  t: Tarjimon;
  /** Tafsilot boshidan ochiqmi (tasdiqlanganlar uchun) */
  ochiq?: boolean;
}) {
  const s = sanoq(natija);
  const narx = narxYoz(natija.narx);
  const kap = qisqaPul(natija.marketCap);
  const hajm = qisqaPul(natija.hajm24s);

  return (
    <article className="rounded-kartochka border-ramka-yumshoq bg-panel border p-3 sm:p-4">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <h3 className="text-sarlavha text-base font-semibold">{natija.symbol}</h3>
        <p className="raqam text-sm">
          <span className="text-matn font-semibold">
            {s.jami}/{s.jamiMax}
          </span>
          <span className="text-matn-past">
            {" · "}
            {t("radar.harakat")} {s.harakat}/{s.harakatMax}
            {" · "}
            {t("radar.yoqilgi")} {s.yoqilgi}/{s.yoqilgiMax}
          </span>
        </p>
        <span className="ml-auto flex flex-wrap items-center gap-1.5">
          {natija.ketmaKet === 1 ? (
            <Badge tone="yaxshi">
              <Ikonka nom="yangilangan" className="h-3 w-3" />
              <span title={t("radar.yangi_izoh")}>{t("radar.yangi")}</span>
            </Badge>
          ) : natija.ketmaKet > 1 ? (
            <Badge tone="neytral">
              <Ikonka nom="yangilash" className="h-3 w-3" />
              {shablon(t("radar.ketma_ket"), { n: natija.ketmaKet })}
            </Badge>
          ) : null}
          <Badge tone={HALOL_TON[natija.halol]}>
            <Ikonka nom={HALOL_IKONKA[natija.halol]} className="h-3 w-3" />
            <span className="sr-only">{t("radar.halol_reestr")}: </span>
            {t(`radar.halol.${natija.halol}`)}
          </Badge>
        </span>
      </header>

      <p className="text-matn-past mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="text-matn raqam">
          {natija.orin !== null
            ? shablon(t("radar.orin"), { n: natija.orin })
            : t("radar.orinsiz")}
        </span>
        <span>
          {t("radar.narx")}: <span className="text-matn raqam">{narx ? `$${narx}` : "—"}</span>
        </span>
        {kap ? (
          <span>
            {t("radar.kapitalizatsiya")}: <span className="text-matn raqam">{kap}</span>
          </span>
        ) : (
          <span className="text-ortacha">{t("radar.kap_nomalum")}</span>
        )}
        {hajm ? (
          <span>
            {t("radar.hajm_24s")}: <span className="text-matn raqam">{hajm}</span>
          </span>
        ) : null}
        {natija.yangiListing ? <Badge tone="ortacha">{t("radar.yangi_listing")}</Badge> : null}
      </p>

      <details className="group mt-3" open={ochiq}>
        <summary className="text-matn-past hover:text-sarlavha flex cursor-pointer list-none items-center gap-2 text-xs select-none">
          <span className="flex items-center gap-1" aria-hidden>
            {natija.tekshiruvlar.map((tek) => (
              <TekshiruvBelgisi key={tek.kod} holat={tek.holat} t={t} className="h-2.5 w-2.5" />
            ))}
          </span>
          {t("radar.tekshiruvlar")}
          <Ikonka nom="pastga" className="h-3.5 w-3.5 transition-transform group-open:rotate-180" />
        </summary>

        <ul className="mt-2 space-y-1.5">
          {natija.tekshiruvlar.map((tek) => (
            <li
              key={tek.kod}
              className="border-ramka-yumshoq/60 flex flex-wrap items-start gap-x-2 gap-y-0.5 border-t pt-1.5 text-xs first:border-t-0 first:pt-0"
            >
              <TekshiruvBelgisi holat={tek.holat} t={t} className="mt-0.5" />
              <span className="text-matn w-36 shrink-0 font-medium">
                {t(`radar.tek.${tek.kod}`)}
              </span>
              <span
                className={cn(
                  "min-w-0 flex-1 raqam",
                  tek.holat === "malumot_yoq" ? "text-matn-past" : "text-matn",
                )}
              >
                {sababMatni(t, tek)}
              </span>
              <span className="text-matn-past w-full pl-5 text-[11px] sm:w-auto sm:pl-0">
                {manbaNomi(t, tek.manba)}
              </span>
            </li>
          ))}
        </ul>

        <p className="text-matn border-ramka-yumshoq mt-3 border-t pt-2 text-xs leading-relaxed">
          {xulosaMatni(t, natija.tekshiruvlar)}
        </p>
      </details>
    </article>
  );
}
