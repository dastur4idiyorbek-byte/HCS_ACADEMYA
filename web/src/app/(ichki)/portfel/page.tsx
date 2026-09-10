import { Qulf } from "@/components/ui/Qulf";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { kotirovka } from "@/lib/config";
import { env } from "@/lib/env";
import { HOLAT_IKONKASI, foiz, holatNomi, narx } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { narxlarniOl } from "@/lib/jonli-server";
import { dashboardQur, type Dashboard } from "@/lib/portfel";
import { portfelXomAshyosi, pozitsiyalar, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { balansSaqlash } from "./amallar";
import { Ikonka } from "@/components/ui/Ikonka";

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
        <Sarlavha matn={t("portfel.sarlavha")} belgi="pul" />
        <Qulf til={til} kerakliTarif="lite" botUsername={env().botUsername} />
      </>
    );
  }

  const royxat = foydalanuvchi ? pozitsiyalar(foydalanuvchi.id) : [];
  const ochiq = royxat.filter((p) => p.closedAt === null);
  const yopiq = royxat.filter((p) => p.closedAt !== null);
  const jamiPnl = yopiq.reduce((s, p) => s + (p.pnlUsd ?? 0), 0);

  // Portfel moduli (3-prompt). Hisob `lib/portfel.ts` da va u Python
  // nusxasiga etalon fayl orqali bog'langan — botdagi bilan bir xil
  // raqam chiqishini test ushlab turadi.
  const xom = foydalanuvchi
    ? portfelXomAshyosi(foydalanuvchi.id)
    : { qismlar: [], ochiqlar: [], bolaklar: [] };
  const narxlar = await narxlarniOl(
    xom.ochiqlar.map((p) => `${p.symbol}${kotirovka()}`),
  );
  const dashboard = dashboardQur(
    xom.qismlar,
    xom.ochiqlar.map((p) => ({
      ...p,
      // Narx olinmasa `null` qoladi: "+$0.00" ko'rsatish "biz
      // bilmaymiz" ni "savdo nolda" ga aylantirardi.
      joriyNarx: narxlar[`${p.symbol}${kotirovka()}`] ?? null,
    })),
    xom.bolaklar,
    foydalanuvchi?.declaredBalanceUsd ?? 0,
  );

  return (
    <>
      <Sarlavha
        matn={t("portfel.sarlavha")}
        izoh={t("portfel.izoh")}
        belgi="pul"
      />

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

          <form
            action={balansSaqlash}
            className="mt-3 flex flex-wrap items-end gap-2"
          >
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
              <Ikonka
                nom="ogohlantirish"
                className="inline h-4 w-4 align-[-3px]"
              />{" "}
              {xato}
            </p>
          )}
          <CardHint className="mt-2">{t("portfel.balans_bosh")}</CardHint>
        </Card>

        <Natija d={dashboard} t={t} />

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
                <h2 className="text-sarlavha mb-3 font-semibold">
                  {t("portfel.ochiq")}
                </h2>
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

/** "Mening natijam" — botdagi ekranning sayt ko'rinishi.
 *
 * RAQAM SHU YERDA HISOBLANMAYDI: `dashboardQur` tayyor holda beradi.
 * Ansiz uchinchi hisob paydo bo'lardi. */
function Natija({ d, t }: { d: Dashboard; t: (k: string) => string }) {
  const baholangan = d.ochiqSoni - d.baholanmaganSoni;

  return (
    <Card>
      <CardTitle>{t("portfel.natijam")}</CardTitle>

      {d.bosh ? (
        <p className="text-matn-past mt-2 text-sm">
          {t("portfel.natijam_bosh")}
        </p>
      ) : (
        <>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
            {d.qatorlar.map((q) => (
              <div key={q.nom}>
                <dt className="text-matn-past text-xs uppercase">{q.nom}</dt>
                <dd
                  className={`raqam font-semibold ${
                    q.usd > 0
                      ? "text-yaxshi"
                      : q.usd < 0
                        ? "text-past"
                        : "text-matn-past"
                  }`}
                >
                  {q.usd >= 0 ? "+" : "−"}${narx(Math.abs(q.usd))}
                  <span className="text-matn-past ml-1 text-xs font-normal">
                    ({foiz(q.pct)})
                  </span>
                </dd>
              </div>
            ))}
          </dl>

          {baholangan > 0 && (
            <p className="text-matn-past mt-3 text-sm">
              {t("portfel.ochiq_natija")}:{" "}
              <span
                className={`raqam font-semibold ${
                  d.unrealizedUsd >= 0 ? "text-yaxshi" : "text-past"
                }`}
              >
                {d.unrealizedUsd >= 0 ? "+" : "−"}$
                {narx(Math.abs(d.unrealizedUsd))}
              </span>{" "}
              <em>({t("portfel.ochiq_natija_izoh")})</em>
            </p>
          )}

          {/* "Narx olinmadi" ni YASHIRMAYMIZ — u nol emas. */}
          {d.baholanmaganSoni > 0 && (
            <p className="text-matn-past mt-1 text-sm">
              {d.baholanmaganSoni} {t("portfel.narx_yoq")}
            </p>
          )}
        </>
      )}

      {d.bandBolaklar.length + d.boshBolaklar.length > 0 && (
        <div className="border-ramka-yumshoq mt-4 border-t pt-3">
          <p className="text-matn-past text-xs uppercase">
            {t("portfel.bolaklar")}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm">
            {d.bandBolaklar.length > 0 && (
              <Badge tone="neytral">
                <Ikonka nom="qulf" className="inline h-4 w-4 align-[-3px]" />{" "}
                {t("portfel.bolak_band")}: {d.bandBolaklar.join(", ")}
              </Badge>
            )}
            {d.boshBolaklar.length > 0 && (
              <Badge tone="yaxshi">
                {t("portfel.bolak_bosh")}: {d.boshBolaklar.length}
              </Badge>
            )}
            <span className="text-matn-past raqam">
              {t("portfel.xavf_ostida")}: {foiz(d.xavfPct)}
            </span>
          </div>
        </div>
      )}
    </Card>
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
        <Ikonka nom={HOLAT_IKONKASI[p.signalStatus]} />
        <span className="text-sarlavha flex-1 font-semibold">{p.symbol}</span>
        <Badge
          tone={
            p.pnlPct === null ? "neytral" : p.pnlPct >= 0 ? "yaxshi" : "past"
          }
        >
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
