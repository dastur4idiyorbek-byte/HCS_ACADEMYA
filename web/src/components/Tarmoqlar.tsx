import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { type Havola, type Ikonka as HavolaTuri } from "@/lib/queries";
import { type Til, tarjimon } from "@/lib/i18n";
import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";

/** Ijtimoiy tarmoq havolalari — bosh sahifa pastida.
 *
 * Ro'yxat bazadan keladi (admin panel orqali boshqariladi), shuning
 * uchun yangi kanal qo'shish uchun kodga tegish shart emas.
 */

/** Havola turi -> HCS ikonkasi.
 *
 * `Ikonka` nomi bazadagi TUR uchun ham ishlatilgan (`queries.ts`),
 * shuning uchun u bu yerda `HavolaTuri` deb chaqiriladi — ikkita
 * "Ikonka" bitta faylda chalkashtirardi. */
const BELGI: Record<HavolaTuri, IkonkaNomi> = {
  telegram: "telegram",
  instagram: "instagram",
  youtube: "youtube",
  web: "havolalar",
};

export function Tarmoqlar({
  havolalar,
  til,
}: {
  havolalar: Havola[];
  til: Til;
}) {
  const t = tarjimon(til);

  return (
    <Card>
      <CardTitle>{t("bosh.tarmoqlar")}</CardTitle>
      {havolalar.length === 0 ? (
        <CardHint>{t("bosh.tarmoqlar_yoq")}</CardHint>
      ) : (
        <ul className="mt-3 flex flex-wrap gap-2">
          {havolalar.map((h) => (
            <li key={h.id}>
              <a
                href={h.url}
                target="_blank"
                // `noopener` — ochilgan sahifa bizning oynamizni boshqara
                // olmasin; `noreferrer` — qayerdan kelgani uzatilmasin.
                rel="noopener noreferrer"
                className="border-ramka-yumshoq rounded-tugma hover:bg-panel-yorqin hover:border-ramka flex items-center gap-2 border px-3 py-2 text-sm transition"
              >
                <Ikonka nom={BELGI[h.icon]} className="h-4 w-4" />
                {h.title}
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
