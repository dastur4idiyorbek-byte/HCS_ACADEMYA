import { Qulf } from "@/components/ui/Qulf";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { env } from "@/lib/env";
import { HOLAT_BELGISI, foiz, holatNomi, narx } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { pozitsiyalar, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { balansSaqlash } from "./amallar";

export const dynamic = "force-dynamic";

export default async function Portfel({
  searchParams,
}: {
  searchParams: Promise<{ xato?: string }>;
}) {
  const { til, tarif, foydalanuvchi } = await kirim();
  const { xato } = await searchParams;
  const t = tarjimon(til);
  if (!tarifQamraydi(tarif, "lite")) {
    return (
      <>
        <Sarlavha matn={t("portfel.sarlavha")} />
        <Qulf til={til} kerakliTarif="lite" botUsername={env().botUsername} />
      </>
    );
  }

  const royxat = foydalanuvchi ? pozitsiyalar(foydalanuvchi.id) : [];
  const ochiq = royxat.filter((p) => p.closedAt === null);
  const yopiq = royxat.filter((p) => p.closedAt !== null);
  const jamiPnl = yopiq.reduce((s, p) => s + (p.pnlUsd ?? 0), 0);

  return (
    <>
      <Sarlavha matn={t("portfel.sarlavha")} izoh={t("portfel.izoh")} />

      <div className="space-y-5">
        {/* Balans TAHRIRLANADI. Avval u faqat o'qish uchun edi va
            kiritilmagan bo'lsa kartochka umuman ko'rinmasdi — ya'ni
            saytdan kirgan odam uni hech qachon kirita olmasdi. Balanssiz
            esa signal kartochkasida "Miqdor" ham hisoblanmaydi. */}
        <Card>
          <CardTitle>{t("portfel.balans")}</CardTitle>
          <p className="raqam text-sarlavha mt-1 text-2xl font-bold">
            {foydalanuvchi?.declaredBalanceUsd === null ||
            foydalanuvchi?.declaredBalanceUsd === undefined
              ? "—"
              : `$${narx(foydalanuvchi.declaredBalanceUsd)}`}
          </p>
          <CardHint>{t("portfel.balans_izoh")}</CardHint>

          <form action={balansSaqlash} className="mt-3 flex flex-wrap items-end gap-2">
            <label className="min-w-0 flex-1">
              <span className="text-matn-past mb-1 block text-xs uppercase">
                {t("portfel.balans_yangi")}
              </span>
              <input
                name="balans"
                inputMode="decimal"
                defaultValue={foydalanuvchi?.declaredBalanceUsd ?? ""}
                placeholder="1000"
                className="border-ramka-yumshoq rounded-tugma bg-fon raqam w-full border px-3 py-2 text-sm"
              />
            </label>
            <Button type="submit">{t("umumiy.saqlash")}</Button>
          </form>

          {xato && (
            <p className="border-past/60 text-past rounded-kichik mt-2 border px-3 py-2 text-sm">
              ⚠️ {xato}
            </p>
          )}
          <CardHint className="mt-2">{t("portfel.balans_bosh")}</CardHint>
        </Card>

        {royxat.length === 0 ? (
          <Card>
            <p className="text-matn-past text-sm">{t("portfel.yoq")}</p>
          </Card>
        ) : (
          <>
            {yopiq.length > 0 && (
              <Card variant="urgu">
                <CardTitle>{t("portfel.jami_natija")}</CardTitle>
                <p
                  className={`raqam mt-1 text-3xl font-bold ${jamiPnl >= 0 ? "text-yaxshi" : "text-past"}`}
                >
                  {jamiPnl >= 0 ? "+" : "−"}${narx(Math.abs(jamiPnl))}
                </p>
                <CardHint>
                  {t("portfel.yopilgan")}: {yopiq.length} {t("umumiy.dona")}
                </CardHint>
              </Card>
            )}

            {ochiq.length > 0 && (
              <section>
                <h2 className="text-sarlavha mb-3 font-semibold">{t("portfel.ochiq")}</h2>
                <div className="space-y-2">
                  {ochiq.map((p) => (
                    <Qator key={p.id} p={p} til={til} t={t} />
                  ))}
                </div>
              </section>
            )}

            {yopiq.length > 0 && (
              <section>
                <h2 className="text-matn-past mb-3 text-sm font-semibold tracking-wide uppercase">
                  {t("portfel.yopilgan")}
                </h2>
                <div className="space-y-2">
                  {yopiq.map((p) => (
                    <Qator key={p.id} p={p} til={til} t={t} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </>
  );
}

function Qator({
  p,
  til,
  t,
}: {
  p: ReturnType<typeof pozitsiyalar>[number];
  til: "uz" | "ru";
  t: (k: string) => string;
}) {
  return (
    <div className="border-ramka-yumshoq bg-panel rounded-kartochka border p-3.5">
      <div className="flex items-center gap-2">
        <span aria-hidden>{HOLAT_BELGISI[p.signalStatus]}</span>
        <span className="text-sarlavha flex-1 font-semibold">{p.symbol}</span>
        <Badge tone={p.pnlPct === null ? "neytral" : p.pnlPct >= 0 ? "yaxshi" : "past"}>
          {p.pnlPct === null ? holatNomi(p.signalStatus, til) : foiz(p.pnlPct)}
        </Badge>
      </div>
      <dl className="text-matn-past mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-4">
        <Kichik nom={t("portfel.hajm")} qiymat={`$${narx(p.amountUsd)}`} />
        <Kichik nom={t("portfel.kirish")} qiymat={narx(p.entryPrice)} />
        <Kichik
          nom={t("portfel.chiqish")}
          qiymat={p.exitPrice === null ? "—" : narx(p.exitPrice)}
        />
        <Kichik
          nom={t("portfel.natija")}
          qiymat={p.pnlUsd === null ? "—" : `$${narx(p.pnlUsd)}`}
        />
      </dl>
    </div>
  );
}

function Kichik({ nom, qiymat }: { nom: string; qiymat: string }) {
  return (
    <div>
      <dt className="uppercase">{nom}</dt>
      <dd className="raqam text-matn font-medium">{qiymat}</dd>
    </div>
  );
}
