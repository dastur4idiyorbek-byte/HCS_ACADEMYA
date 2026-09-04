import Image from "next/image";

import { Tarmoqlar } from "@/components/Tarmoqlar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { tarjimon } from "@/lib/i18n";
import { havolalar } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function Bosh() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const tarmoqlar = havolalar();

  return (
    <div className="space-y-5">
      <header className="flex flex-col items-center py-6 text-center">
        <Image
          src="/logo.jpg"
          alt="HCS — Halol Crypto Savdo"
          width={96}
          height={96}
          className="rounded-kartochka"
          priority
        />
        <h1 className="text-sarlavha mt-4 text-2xl font-bold tracking-wide sm:text-3xl">
          HALOL CRYPTO SAVDO
        </h1>
        <p className="text-matn-past mt-1 text-sm">{t("bosh.shior")}</p>
      </header>

      <Card>
        <CardTitle>{t("bosh.tavsif_sarlavha")}</CardTitle>
        <p className="mt-2 text-sm leading-relaxed">{t("bosh.tavsif")}</p>
      </Card>

      <div className="grid gap-5 sm:grid-cols-2">
        <Card>
          <CardTitle>{t("bosh.kimga_sarlavha")}</CardTitle>
          <p className="mt-2 text-sm leading-relaxed">{t("bosh.kimga")}</p>
        </Card>

        <Card>
          <CardTitle>{t("bosh.nega_halol_sarlavha")}</CardTitle>
          <p className="mt-2 text-sm leading-relaxed">{t("bosh.nega_halol")}</p>
        </Card>
      </div>

      {/* Diniy asos — matn ATAYLAB yozilmagan.
          Iqtibosning aniq lafzi bilimdon kishi tasdiqlagandan keyin
          kiritiladi. Bu joy dizayn jihatdan tayyor: matn almashtirilsa
          kifoya, boshqa hech narsa o'zgarmaydi. */}
      <Card variant="urgu">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>☪️ {t("bosh.diniy_sarlavha")}</CardTitle>
          <Badge tone="ortacha">{t("bosh.diniy_holat")}</Badge>
        </div>
        <p className="text-matn-past mt-3 text-sm leading-relaxed italic">
          {t("bosh.diniy_placeholder")}
        </p>
        <CardHint className="mt-3">{t("bosh.diniy_izoh")}</CardHint>
      </Card>

      <Tarmoqlar havolalar={tarmoqlar} til={til} />
    </div>
  );
}
