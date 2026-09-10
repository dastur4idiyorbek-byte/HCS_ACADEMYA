import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { tarjimon } from "@/lib/i18n";
import { boshPostlar, boshPostlarSoni } from "@/lib/queries";
import { kirim } from "@/lib/session";
import { sana } from "@/lib/format";

import { boshPostOchir } from "../amallar";
import { PostYuklagich } from "./yuklagich";
import { Ikonka } from "@/components/ui/Ikonka";

export const dynamic = "force-dynamic";

/** Bosh sahifa oqimini boshqarish (4-prompt, 1-qism).
 *
 * Tanishtiruv, diniy asos va ijtimoiy tarmoqlar bu yerda KO'RINMAYDI
 * va o'chirilmaydi — ular oqimning tepasida, kodda turadi. Diniy
 * iqtibos joyi olim tasdiqlaguncha placeholder bo'lishi shart,
 * shuning uchun uni o'chirib bo'ladigan postga aylantirmadik.
 */
export default async function AdminPostlar({
  searchParams,
}: {
  searchParams: Promise<{ xato?: string }>;
}) {
  const { til } = await kirim();
  const { xato } = await searchParams;
  const t = tarjimon(til);
  const postlar = boshPostlar(30);
  const jami = boshPostlarSoni();

  return (
    <div className="space-y-5">
      <Card>
        <CardTitle>{t("admin.post_yangi")}</CardTitle>
        <CardHint className="mt-1">{t("admin.post_izoh")}</CardHint>
        {xato && (
          <p className="text-past mt-3 text-sm" role="alert">
            <Ikonka
              nom="ogohlantirish"
              className="inline h-4 w-4 align-[-3px]"
            />{" "}
            {xato}
          </p>
        )}
        <PostYuklagich til={til} />
      </Card>

      <section>
        <h2 className="text-matn-past mb-3 text-sm font-semibold tracking-wide uppercase">
          {t("admin.post_royxat")} ({jami})
        </h2>

        {postlar.length === 0 ? (
          <Card>
            <p className="text-matn-past text-sm">{t("admin.post_yoq")}</p>
          </Card>
        ) : (
          <div className="space-y-2">
            {postlar.map((p) => (
              <div
                key={p.id}
                className="border-ramka-yumshoq bg-panel rounded-kartochka border p-3.5"
              >
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-matn-past text-xs">
                      #{p.id} · {sana(p.yaratilgan)} · {p.turi}
                    </p>
                    {p.matn && (
                      <p className="mt-1.5 line-clamp-3 text-sm whitespace-pre-wrap">
                        {p.matn}
                      </p>
                    )}
                    {p.mediaTuri === "image" && p.media && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={`/api/post-media/${p.media}`}
                        alt=""
                        className="rounded-tugma mt-2 max-h-32"
                      />
                    )}
                    {p.mediaTuri === "audio" && p.media && (
                      <audio
                        controls
                        src={`/api/post-media/${p.media}`}
                        className="mt-2 w-full max-w-sm"
                      />
                    )}
                  </div>

                  <form action={boshPostOchir}>
                    <input type="hidden" name="id" value={p.id} />
                    <Button type="submit" variant="ikkilamchi">
                      {t("umumiy.ochirish")}
                    </Button>
                  </form>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
