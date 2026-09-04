import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

export default async function Kurs() {
  const { til } = await kirim();
  const t = tarjimon(til);

  return (
    <>
      <Sarlavha
        matn={t("kontent.kurs")}
        ong={<Badge tone="ortacha">{t("kontent.tez_kunda")}</Badge>}
      />
      <Card variant="urgu">
        <CardTitle>🎓 {t("kontent.tez_kunda")}</CardTitle>
        <CardHint>{t("kontent.kurs_izoh")}</CardHint>
      </Card>
    </>
  );
}
