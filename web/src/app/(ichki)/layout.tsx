import { redirect } from "next/navigation";

import { BolimTablari } from "@/components/BolimTablari";
import { PastkiNav } from "@/components/PastkiNav";
import { TilTanlov } from "@/components/TilTanlov";
import { Yon } from "@/components/Yon";
import { PASTKI_TABLAR, korinadiganBandlar, tabSahifalari } from "@/lib/menyu";
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

  // Pastki nav uchun 5 bo'lim. Har bir tabning sahifalari `menyu.ts`
  // dan olinadi; qulf hisobi yon paneldagi bilan AYNAN bir xil.
  const pastkiTablar = PASTKI_TABLAR.map((tab) => ({
    kod: tab.kod,
    nom: t(tab.kalit),
    sahifalar: tabSahifalari(tab, admin).map((band) => ({
      yol: band.yol,
      nom: t(band.kalit),
      qulf: band.talab !== null && !tarifQamraydi(tarif, band.talab),
      tezKunda: Boolean(band.tezKunda),
    })),
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
      {/* Mobil uchun pastki bo'shliq: pastki nav kontentni yopmasin.
          Desktopda yon panel bor, qo'shimcha bo'shliq kerak emas. */}
      <main className="min-w-0 flex-1 px-4 pt-6 pb-24 sm:px-6 sm:pt-8 lg:pb-8">
        <div className="mx-auto max-w-4xl">
          <BolimTablari tablar={pastkiTablar} />
          {children}
        </div>
      </main>
      <PastkiNav tablar={pastkiTablar} qulfMatn={t("qulf.sarlavha")} />
    </div>
  );
}
