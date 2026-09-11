import Link from "next/link";
import { notFound } from "next/navigation";

import { KitobBobi } from "@/components/KitobMatni";
import { Card } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { Qulf } from "@/components/ui/Qulf";
import { env } from "@/lib/env";
import { tarjimon } from "@/lib/i18n";
import { KITOB_BOLIMLARI, KITOB_TARIFI, bolimYonidagi } from "@/lib/kitob";
import { kitobBolimi } from "@/lib/kitob-server";
import { tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Kitobning bitta bo'limi — saytda O'QISH uchun.
 *
 * PDF yuklab olish qoladi, lekin kitobni o'qish uchun uni yuklash
 * SHART EMAS: mundarijadagi bo'limni bosgan odam shu yerda to'liq
 * matnni oladi.
 */
export default async function KitobBolimSahifasi({
  params,
}: {
  params: Promise<{ bolim: string }>;
}) {
  const { til, tarif } = await kirim();
  const t = tarjimon(til);
  const { bolim } = await params;

  const tavsif = KITOB_BOLIMLARI.find((b) => b.kalit === bolim);
  if (!tavsif) notFound();

  if (!tarifQamraydi(tarif, KITOB_TARIFI)) {
    return <Qulf til={til} kerakliTarif={KITOB_TARIFI} botUsername={env().botUsername} />;
  }

  const mazmun = await kitobBolimi(bolim);
  if (!mazmun || mazmun.boblar.length === 0) {
    return (
      <Card>
        <p className="text-matn-past text-sm">{t("kitob.tayyor_emas")}</p>
      </Card>
    );
  }

  const { oldingi, keyingi } = bolimYonidagi(bolim);

  return (
    <>
      <Link
        href="/kitob"
        className="text-matn-past hover:text-sarlavha inline-flex items-center gap-1.5 text-sm"
      >
        <Ikonka nom="tepaga" className="h-4 w-4 -rotate-90" />
        {t("kitob.mundarijaga")}
      </Link>

      <h1 className="text-ramka mt-3 mb-1 text-sm font-bold uppercase">
        {t(`kitob.${bolim}`)}
      </h1>

      {/* Bobga sakrash — uzun bo'limda (masalan 6 bobli 3-bo'lim)
          o'quvchi kerakli joyni izlab skroll qilmasin. */}
      {mazmun.boblar.length > 1 && (
        <Card className="my-4">
          <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm">
            {mazmun.boblar.map((b) => (
              <li key={b.raqam}>
                <a
                  href={`#${b.raqam.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                  className="hover:text-sarlavha"
                >
                  <span className="text-matn-past">{b.raqam}</span> {b.nom}
                </a>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="space-y-10">
        {mazmun.boblar.map((b) => (
          <KitobBobi
            key={b.raqam}
            raqam={b.raqam}
            nom={b.nom}
            bloklar={b.bloklar}
            t={t}
          />
        ))}
      </div>

      <div className="border-ramka-yumshoq mt-10 flex items-center justify-between gap-4 border-t pt-5 text-sm">
        {oldingi ? (
          <Link href={`/kitob/${oldingi}`} className="hover:text-sarlavha">
            ← {t(`kitob.${oldingi}`)}
          </Link>
        ) : (
          <span />
        )}
        {keyingi ? (
          <Link href={`/kitob/${keyingi}`} className="hover:text-sarlavha text-right">
            {t(`kitob.${keyingi}`)} →
          </Link>
        ) : (
          <span />
        )}
      </div>
    </>
  );
}
