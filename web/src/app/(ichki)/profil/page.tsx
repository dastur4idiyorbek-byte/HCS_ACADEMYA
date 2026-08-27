import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { botHavolasi, env } from "@/lib/env";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { kutilayotganTolovBor, narxlar, oxirgiObuna } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function Profil() {
  const { til, foydalanuvchi, obuna, admin } = await kirim();
  const t = tarjimon(til);
  const botUsername = env().botUsername;

  const oxirgi = foydalanuvchi ? oxirgiObuna(foydalanuvchi.id) : null;
  const kutilmoqda = foydalanuvchi ? kutilayotganTolovBor(foydalanuvchi.id) : false;
  const narxRoyxati = narxlar();

  const faol = obuna !== null;
  const tugagan = !faol && oxirgi !== null;

  return (
    <>
      <Sarlavha
        matn={t("profil.sarlavha")}
        ong={admin ? <Badge tone="ortacha">ADMIN</Badge> : undefined}
      />

      <div className="space-y-5">
        <Card>
          <CardTitle>{foydalanuvchi?.fullName ?? t("profil.sarlavha")}</CardTitle>
          <CardHint>
            {foydalanuvchi?.username ? `@${foydalanuvchi.username} · ` : ""}
            ID {foydalanuvchi?.telegramId ?? "—"}
          </CardHint>
        </Card>

        <Card variant="urgu">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>{t("profil.obuna")}</CardTitle>
            {faol ? (
              <Badge tone="yaxshi">{obuna.tier.toUpperCase()}</Badge>
            ) : (
              <Badge tone="past">{tugagan ? t("profil.tugadi") : t("profil.yoq")}</Badge>
            )}
          </div>

          {faol && (
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-matn-past">{t("profil.tarif")}</dt>
                <dd className="font-semibold">{obuna.tier}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-matn-past">{t("profil.muddat")}</dt>
                <dd className="raqam font-semibold">{sana(obuna.expiresAt)} UTC</dd>
              </div>
            </dl>
          )}

          {tugagan && (
            <CardHint className="mt-2">
              {t("profil.tugadi")}: {sana(oxirgi.expiresAt)} UTC
            </CardHint>
          )}

          {kutilmoqda && (
            <p className="border-ramka text-sarlavha rounded-kichik mt-3 border px-3 py-2 text-sm">
              ⏳ {t("profil.kutilmoqda")}
            </p>
          )}

          <div className="mt-4">
            <Button href={botHavolasi(botUsername)}>
              {faol ? t("profil.uzaytirish") : t("profil.tolov")}
            </Button>
          </div>
          <CardHint className="mt-3">{t("profil.tolov_izoh")}</CardHint>
        </Card>

        {narxRoyxati.length > 0 && (
          <Card>
            <CardTitle>{t("profil.narxlar")}</CardTitle>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-matn-past text-left text-xs uppercase">
                    <th className="pb-2 font-medium">{t("profil.tarif")}</th>
                    <th className="pb-2 font-medium">{t("statistika.davr")}</th>
                    <th className="pb-2 text-right font-medium">{t("admin.summa")}</th>
                  </tr>
                </thead>
                <tbody>
                  {narxRoyxati.map((n) => (
                    <tr key={`${n.tier}-${n.period}-${n.currency}`} className="border-t border-white/5">
                      <td className="py-2 font-medium">{n.tier}</td>
                      <td className="text-matn-past py-2">
                        {n.period === "daily" ? t("profil.kunlik") : t("profil.oylik")}
                      </td>
                      <td className="raqam py-2 text-right font-semibold">
                        {n.amount.toLocaleString("en-US")} {n.currency}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
