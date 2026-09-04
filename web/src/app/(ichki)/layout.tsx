import { redirect } from "next/navigation";

import { TilTanlov } from "@/components/TilTanlov";
import { Yon } from "@/components/Yon";
import { korinadiganBandlar } from "@/lib/menyu";
import { tarjimon } from "@/lib/i18n";
import { tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

/** Ichki bo'limlarning umumiy ramkasi.
 *
 * Kirmagan foydalanuvchi bu yerga umuman yetib kelmaydi — sahifa
 * ma'lumotni YUKLAMASDAN oldin `/kirish` ga yo'naltiriladi. Bu "qulf
 * ko'rsatib, ma'lumotni HTML ichida yuborish" xatosining oldini oladi.
 */
export default async function IchkiLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { kirgan, tarif, admin, til } = await kirim();
  if (!kirgan) redirect("/kirish");

  const t = tarjimon(til);
  const bandlar = korinadiganBandlar(admin).map((b) => ({
    yol: b.yol,
    nom: t(b.kalit),
    belgi: b.belgi,
    qulf: b.talab !== null && !tarifQamraydi(tarif, b.talab),
    tezKunda: Boolean(b.tezKunda),
  }));

  return (
    <div className="lg:flex">
      <Yon
        bandlar={bandlar}
        tarifYorliq={
          admin ? "ADMIN" : (tarif?.toUpperCase() ?? t("profil.yoq"))
        }
        chiqishMatn={t("umumiy.chiqish")}
        tilTanlov={<TilTanlov joriy={til} />}
      />
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 sm:py-8">
        <div className="mx-auto max-w-4xl">{children}</div>
      </main>
    </div>
  );
}
