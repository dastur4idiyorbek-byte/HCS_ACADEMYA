import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { Qulf } from "@/components/ui/Qulf";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { env } from "@/lib/env";
import { tarjimon } from "@/lib/i18n";
import { KITOB_BOLIMLARI, KITOB_TARIFI } from "@/lib/kitob";
import { tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Kitob sahifasi — tavsif va yuklab olish.
 *
 * FAYLNING O'ZI BU YERDA TURMAYDI. Yuklash `api/kitob` orqali
 * bo'ladi va u yerda obuna qayta tekshiriladi. Sahifadagi qulf —
 * qulaylik uchun; haqiqiy darvoza server tomonda.
 */
export default async function Kitob() {
  const { til, tarif } = await kirim();
  const t = tarjimon(til);

  if (!tarifQamraydi(tarif, KITOB_TARIFI)) {
    return (
      <>
        <Sarlavha matn={t("kitob.sarlavha")} belgi="kurs" />
        <Qulf til={til} kerakliTarif={KITOB_TARIFI} botUsername={env().botUsername} />
      </>
    );
  }

  return (
    <>
      <Sarlavha
        matn={t("kitob.sarlavha")}
        izoh={t("kitob.izoh")}
        belgi="kurs"
      />

      <div className="space-y-5">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Ikonka nom="maqolalar" />
                {t("kitob.sarlavha")}
              </CardTitle>
              <p className="text-matn-past mt-1 text-sm">{t("kitob.hajm")}</p>
            </div>
            {/* Oddiy havola — `download` atributi shart emas:
                server `content-disposition: attachment` yuboradi. */}
            <a
              href="/api/kitob"
              className="bg-ramka rounded-tugma text-fon inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold"
            >
              <Ikonka nom="pastga" className="h-4 w-4" />
              {t("kitob.yuklash")}
            </a>
          </div>
          <CardHint className="mt-4">{t("kitob.ogohlantirish")}</CardHint>
        </Card>

        <Card>
          <CardTitle className="flex items-center gap-2">
            <Ikonka nom="akademiya" />
            {t("kitob.tarkib")}
          </CardTitle>
          <CardHint className="mt-1 mb-3">{t("kitob.tarkib_izoh")}</CardHint>
          {/* HAR BO'LIM — HAVOLA. Ilgari bu oddiy ro'yxat edi va
              odam bosib ko'rib, hech narsa ochilmagach chalkashardi.
              Kitobni o'qish uchun PDF yuklash SHART EMAS. */}
          <ul className="space-y-1.5">
            {KITOB_BOLIMLARI.map((b, i) => (
              <li key={b.kalit}>
                <Link
                  href={`/kitob/${b.kalit}`}
                  className="border-ramka-yumshoq hover:border-ramka hover:bg-panel-yorqin rounded-tugma flex items-center gap-3 border px-3 py-2.5 text-sm transition-colors"
                >
                  <span className="text-ramka raqam w-5 shrink-0 text-center font-bold">
                    {i + 1}
                  </span>
                  <span className="flex-1">{t(`kitob.${b.kalit}`)}</span>
                  {b.boblar !== "—" && (
                    <Badge tone="neytral">
                      {b.boblar} {t("kitob.boblar")}
                    </Badge>
                  )}
                  <Ikonka nom="ochish" className="text-matn-past h-4 w-4" />
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle className="flex items-center gap-2">
            <Ikonka nom="malumot" />
            {t("kitob.kimga")}
          </CardTitle>
          <p className="mt-2 text-sm">{t("kitob.kimga_matn")}</p>
        </Card>
      </div>
    </>
  );
}
