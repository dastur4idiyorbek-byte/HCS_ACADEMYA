import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { botHavolasi } from "@/lib/env";
import { type Til, tarjimon } from "@/lib/i18n";
import type { Tarif } from "@/lib/queries";

/** Obunasi yetmagan foydalanuvchiga ko'rsatiladigan ekran.
 *
 * Diqqat: bu YASHIRISH emas, TO'SISH. Ma'lumot serverda ham yuklanmaydi —
 * sahifa umuman so'rov yubormaydi. Aks holda "qulflangan" kartochkaning
 * ichidagi narx HTML manbasida ko'rinib turardi.
 */
export function Qulf({
  til,
  kerakliTarif,
  botUsername,
}: {
  til: Til;
  kerakliTarif: Tarif;
  botUsername: string;
}) {
  const t = tarjimon(til);
  return (
    <Card variant="urgu">
      <CardTitle>🔒 {t("qulf.sarlavha")}</CardTitle>
      <CardHint>{t("qulf.izoh")}</CardHint>
      <p className="text-matn-past mt-3 text-sm">
        {t("qulf.kerak")}:{" "}
        <span className="text-sarlavha font-semibold">{kerakliTarif}</span>
      </p>
      <div className="mt-4">
        <Button href={botHavolasi(botUsername)}>{t("profil.tolov")}</Button>
      </div>
      <CardHint className="mt-3">{t("profil.tolov_izoh")}</CardHint>
    </Card>
  );
}
