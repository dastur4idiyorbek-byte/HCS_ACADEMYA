import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { type Havola, type Ikonka } from "@/lib/queries";
import { type Til, tarjimon } from "@/lib/i18n";

/** Ijtimoiy tarmoq havolalari — bosh sahifa pastida.
 *
 * Ro'yxat bazadan keladi (admin panel orqali boshqariladi), shuning
 * uchun yangi kanal qo'shish uchun kodga tegish shart emas.
 */

const BELGI: Record<Ikonka, string> = {
  telegram: "✈️",
  instagram: "📷",
  youtube: "▶️",
  web: "🔗",
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
                <span aria-hidden>{BELGI[h.icon]}</span>
                {h.title}
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
