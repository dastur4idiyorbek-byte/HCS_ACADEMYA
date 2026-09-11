import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import type { Blok } from "@/lib/kitob-server";

/** Kitob bloklarini ekranga chiqaradi.
 *
 * HTML MANBASI ISHONCHLI: u `scripts/kitob/eksport.py` tomonidan
 * o'z matnimizdan yasaladi, foydalanuvchidan kelmaydi. Shuning
 * uchun `dangerouslySetInnerHTML` bu yerda o'rinli — boshqa yo'l
 * bilan qalin atamalarni saqlab bo'lmasdi.
 */

function Matn({ matn, uslub }: { matn: string; uslub: string }) {
  return <p className={uslub} dangerouslySetInnerHTML={{ __html: matn }} />;
}

export function KitobBlok({ blok, t }: { blok: Blok; t: (k: string) => string }) {
  switch (blok.tur) {
    case "savol":
      return (
        // Bob savoldan boshlanadi — PDF dagi kabi, chap chetida
        // apelsin chiziq bilan.
        <div className="border-ramka bg-panel rounded-kartochka my-4 border-l-4 px-4 py-3">
          <p
            className="text-sarlavha text-[15px] leading-relaxed"
            dangerouslySetInnerHTML={{ __html: blok.matn }}
          />
        </div>
      );

    case "h2":
      return (
        <h2
          className="text-sarlavha mt-7 mb-2 text-lg font-bold"
          dangerouslySetInnerHTML={{ __html: blok.matn }}
        />
      );

    case "h3":
      return (
        <h3
          className="mt-5 mb-1.5 font-semibold"
          dangerouslySetInnerHTML={{ __html: blok.matn }}
        />
      );

    case "matn":
      return <Matn matn={blok.matn} uslub="my-2.5 leading-relaxed" />;

    case "royxat":
      return <Matn matn={blok.matn} uslub="my-1.5 pl-4 leading-relaxed" />;

    case "izoh":
      return <Matn matn={blok.matn} uslub="text-matn-past my-2 text-sm" />;

    case "chizma":
      return (
        // CHIZMA OQ FONDA. U kitob uchun (bosma) chizilgan va
        // ichidagi matn to'q rangda. To'q fonda u o'qilmay qolardi,
        // shuning uchun oq kartochka ichida ko'rsatiladi.
        <div className="rounded-kartochka my-4 overflow-x-auto bg-white p-3">
          <div
            className="[&>svg]:h-auto [&>svg]:w-full [&>svg]:min-w-[520px]"
            dangerouslySetInnerHTML={{ __html: blok.svg }}
          />
        </div>
      );

    case "chizma_izoh":
      return (
        <Matn
          matn={blok.matn}
          uslub="text-matn-past -mt-2 mb-4 text-center text-xs"
        />
      );

    case "xulosa":
      return (
        <Card className="my-5">
          <CardTitle className="flex items-center gap-2 text-base">
            <Ikonka nom="tasdiq" />
            {t("kitob.xulosa")}
          </CardTitle>
          <ul className="mt-2 space-y-1.5 text-sm">
            {blok.qatorlar.map((q, i) => (
              <li key={i} dangerouslySetInnerHTML={{ __html: q }} />
            ))}
          </ul>
        </Card>
      );

    case "savollar":
      return (
        <Card className="my-5">
          <CardTitle className="flex items-center gap-2 text-base">
            <Ikonka nom="testlar" />
            {t("kitob.savollar")}
          </CardTitle>
          <ol className="mt-2 space-y-1.5 text-sm">
            {blok.qatorlar.map((q, i) => (
              <li key={i} dangerouslySetInnerHTML={{ __html: q }} />
            ))}
          </ol>
        </Card>
      );

    case "real_misol":
      return (
        // Admin to'ldiradigan joy. U SAYTDA HAM KO'RINADI: yashirsak,
        // kitobning qaysi joyi hali tugallanmaganini hech kim
        // bilmasdi.
        <div className="border-ramka rounded-kartochka my-4 border border-dashed px-4 py-3">
          <p className="text-ramka flex items-center gap-2 text-xs font-bold">
            <Ikonka nom="grafik" className="h-4 w-4" />
            {t("kitob.real_misol")}
          </p>
          {blok.qatorlar.map((q, i) => (
            <p
              key={i}
              className="text-matn-past mt-1.5 text-sm"
              dangerouslySetInnerHTML={{ __html: q }}
            />
          ))}
        </div>
      );

    case "jadval":
      return (
        <div className="my-4 overflow-x-auto">
          <table className="w-full min-w-[420px] border-collapse text-sm">
            <thead>
              <tr>
                {blok.sarlavha.map((s, i) => (
                  <th
                    key={i}
                    className="border-ramka-yumshoq bg-panel text-sarlavha border px-3 py-2 text-left font-semibold"
                    dangerouslySetInnerHTML={{ __html: s }}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {blok.qatorlar.map((q, i) => (
                <tr key={i}>
                  {q.map((k, j) => (
                    <td
                      key={j}
                      className="border-ramka-yumshoq border px-3 py-2 align-top"
                      dangerouslySetInnerHTML={{ __html: k }}
                    />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
  }
}

export function KitobBobi({
  raqam,
  nom,
  bloklar,
  t,
}: {
  raqam: string;
  nom: string;
  bloklar: Blok[];
  t: (k: string) => string;
}) {
  return (
    <section id={raqam.toLowerCase().replace(/[^a-z0-9]+/g, "-")}>
      <Badge tone="neytral">{raqam}</Badge>
      <h1 className="text-sarlavha mt-2 mb-1 text-2xl font-bold">{nom}</h1>
      {bloklar.map((b, i) => (
        <KitobBlok key={i} blok={b} t={t} />
      ))}
    </section>
  );
}
