import { SalomatlikShkalasi, SalomatlikYoq } from "@/components/Salomatlik";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { salomatlikBandlari } from "@/lib/config";
import { tarjimon } from "@/lib/i18n";
import { kirimMumkinSignallar } from "@/lib/sahifa";
import { salomatlikOxirgi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function Bosh() {
  const { til, foydalanuvchi, tarif } = await kirim();
  const t = tarjimon(til);
  const salomatlik = salomatlikOxirgi();
  const bandlar = salomatlikBandlari();
  const { faol, jami } = kirimMumkinSignallar(tarif);

  const omillar = salomatlik
    ? [
        { kalit: "salomatlik.kenglik", qiymat: salomatlik.trendBreadthScore },
        { kalit: "salomatlik.dominatsiya", qiymat: salomatlik.btcDominanceScore },
        { kalit: "salomatlik.volatillik", qiymat: salomatlik.volatilityScore },
        { kalit: "salomatlik.sigim", qiymat: salomatlik.userCapacityScore },
        { kalit: "salomatlik.toyinganlik", qiymat: salomatlik.saturationScore },
      ].filter((o) => o.qiymat !== null)
    : [];

  return (
    <>
      <Sarlavha
        matn={
          foydalanuvchi?.fullName
            ? `${t("menyu.bosh")} — ${foydalanuvchi.fullName}`
            : t("menyu.bosh")
        }
      />

      <div className="space-y-5">
        <Card variant="urgu">
          <CardTitle>{t("salomatlik.sarlavha")}</CardTitle>
          <CardHint>{t("salomatlik.izoh")}</CardHint>
          <div className="mt-4">
            {salomatlik ? (
              <SalomatlikShkalasi
                qiymat={salomatlik.value}
                band={salomatlik.band}
                bandlar={bandlar}
                til={til}
              />
            ) : (
              <SalomatlikYoq til={til} />
            )}
          </div>
          {salomatlik?.createdAt && (
            <p className="text-matn-past mt-3 text-center text-xs">
              {t("umumiy.yangilangan")}: {salomatlik.createdAt.toISOString().slice(0, 16).replace("T", " ")} UTC
            </p>
          )}
        </Card>

        {omillar.length > 0 && (
          <Card>
            <CardTitle>{t("salomatlik.omillar")}</CardTitle>
            <ul className="mt-3 space-y-2">
              {omillar.map((o) => (
                <li key={o.kalit} className="flex items-center gap-3">
                  <span className="w-40 shrink-0 text-sm">{t(o.kalit)}</span>
                  <span className="bg-fon h-2 flex-1 overflow-hidden rounded-full">
                    <span
                      className="bg-yaxshi block h-full rounded-full"
                      style={{ width: `${Math.min(100, Math.max(0, o.qiymat!))}%` }}
                    />
                  </span>
                  <span className="raqam text-matn-past w-10 text-right text-xs">
                    {o.qiymat!.toFixed(0)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        <div className="grid gap-5 sm:grid-cols-2">
          <Card>
            <CardTitle>{t("signal.sarlavha")}</CardTitle>
            <p className="raqam text-sarlavha mt-2 text-3xl font-bold">{faol}</p>
            <CardHint>
              {t("signal.faol")} · {t("umumiy.jami")}: {jami}
            </CardHint>
            <div className="mt-4">
              <Button href="/signallar" variant="ikkilamchi">
                {t("menyu.signallar")}
              </Button>
            </div>
          </Card>

          <Card>
            <CardTitle>{t("sokinlik.sarlavha")}</CardTitle>
            <CardHint>{t("sokinlik.izoh")}</CardHint>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button href="/sokinlik" variant="ikkilamchi">
                {t("signal.nega_yoq")}
              </Button>
              <Badge>{t("sokinlik.davr")}</Badge>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
