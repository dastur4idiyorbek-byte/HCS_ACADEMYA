import { Badge } from "@/components/ui/Badge";
import { Ikonka } from "@/components/ui/Ikonka";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

/** Modul 4.0.0 — hali tayyor emas. Tarkibi keyin qo'shiladi. */
export default async function Modul4() {
  const { til } = await kirim();
  const t = tarjimon(til);

  return (
    <>
      <Sarlavha
        matn={t("modul.v4")}
        ong={<Badge tone="ortacha">{t("kontent.tez_kunda")}</Badge>}
        belgi="korish"
      />
      <Card variant="urgu">
        <CardTitle className="flex items-center gap-2">
          <Ikonka nom="korish" />
          {t("kontent.tez_kunda")}
        </CardTitle>
        <CardHint>{t("modul.v4_izoh")}</CardHint>
      </Card>
    </>
  );
}
