import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { type HalolHolat, coinQarorlari } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { qarorOchir, qarorSaqla } from "../amallar";

export const dynamic = "force-dynamic";

const HOLATLAR: HalolHolat[] = ["halal", "mashbooh", "haram"];

const TON: Record<HalolHolat, BadgeTone> = {
  halal: "yaxshi",
  mashbooh: "ortacha",
  haram: "past",
};

const BELGI: Record<HalolHolat, string> = {
  halal: "✅",
  mashbooh: "⚠️",
  haram: "🚫",
};

export default async function Halol() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const qarorlar = coinQarorlari();

  return (
    <>
      <Sarlavha matn={`☪️ ${t("admin.halol")}`} izoh={t("admin.halol_izoh")} />

      <div className="space-y-5">
        <Card variant="urgu">
          <CardTitle>{t("admin.qoshish")}</CardTitle>
          <CardHint>{t("admin.sabab_shart")}</CardHint>

          <form action={qarorSaqla} className="mt-4 space-y-3">
            <div className="flex flex-wrap gap-2">
              <label className="sr-only" htmlFor="symbol">
                {t("admin.symbol")}
              </label>
              <input
                id="symbol"
                name="symbol"
                required
                placeholder={t("admin.symbol")}
                className="border-ramka-yumshoq rounded-tugma bg-fon w-40 border px-3 py-2 text-sm uppercase"
              />
              <label className="sr-only" htmlFor="status">
                {t("signal.holat")}
              </label>
              <select
                id="status"
                name="status"
                defaultValue="haram"
                className="border-ramka-yumshoq rounded-tugma bg-fon border px-3 py-2 text-sm"
              >
                {HOLATLAR.map((h) => (
                  <option key={h} value={h}>
                    {BELGI[h]} {t(`admin.${h}`)}
                  </option>
                ))}
              </select>
            </div>
            <input
              name="reason"
              required
              placeholder={t("admin.sabab")}
              className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
            />
            <button
              type="submit"
              className="bg-ramka rounded-tugma px-4 py-2 text-sm font-semibold text-[#0a2450] hover:brightness-110"
            >
              {t("admin.saqlash")}
            </button>
          </form>
        </Card>

        <p className="border-ortacha/60 text-ortacha rounded-kichik border px-3 py-2 text-sm">
          ⚠️ {t("admin.halol_ogoh")}
        </p>

        {HOLATLAR.map((holat) => {
          const guruh = qarorlar.filter((q) => q.status === holat);
          if (guruh.length === 0) return null;
          return (
            <Card key={holat}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle>
                  {BELGI[holat]} {t(`admin.${holat}`)}
                </CardTitle>
                <Badge tone={TON[holat]}>{guruh.length}</Badge>
              </div>

              <ul className="mt-3 space-y-2">
                {guruh.map((q) => (
                  <li
                    key={q.symbol}
                    className="border-ramka-yumshoq rounded-kichik border p-3"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <span className="min-w-0">
                        <span className="text-sarlavha block text-sm font-semibold">
                          {q.symbol}
                        </span>
                        <span className="text-matn-past block text-xs">
                          {q.reason}
                        </span>
                      </span>
                      <form action={qarorOchir}>
                        <input type="hidden" name="symbol" value={q.symbol} />
                        <button
                          type="submit"
                          className="border-past/70 text-past rounded-tugma border px-2.5 py-1 text-xs"
                        >
                          {t("admin.ochirish")}
                        </button>
                      </form>
                    </div>
                    <p className="text-matn-past raqam mt-1.5 text-[11px]">
                      {q.source ?? "—"} · {sana(q.updatedAt)}
                      {q.setBy ? ` · ${t("admin.kim")}: ${q.setBy}` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            </Card>
          );
        })}
      </div>
    </>
  );
}
