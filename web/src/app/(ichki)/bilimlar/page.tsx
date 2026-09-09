import Link from "next/link";

import { Card, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { oqishVaqti } from "@/lib/akademiya";
import { tarjimon } from "@/lib/i18n";
import { kontent, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Bilimlar — maqolalar ro'yxati.
 *
 * QULFLANGAN MAQOLA HAM KO'RINADI, lekin faqat sarlavhasi va qisqa
 * tavsifi. Matnning o'zi serverda to'siladi (`[id]/page.tsx`).
 * Sabab: sarlavha — sotiladigan qiymat, matn esa mahsulot.
 */
export default async function Bilimlar() {
  const { til, tarif } = await kirim();
  const t = tarjimon(til);

  const maqolalar = kontent().filter((k) => k.kind === "maqola");

  return (
    <>
      <Sarlavha
        matn={t("akademiya.bilimlar")}
        izoh={t("akademiya.bilimlar_izoh")}
      />

      {maqolalar.length === 0 ? (
        <Card>
          <p className="text-matn-past text-sm">{t("kontent.yoq")}</p>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {maqolalar.map((m) => {
            const qulf = !tarifQamraydi(tarif, m.minTier);
            const vaqt = oqishVaqti(m.davomiylik, t("akademiya.daqiqa"));
            return (
              <Link
                key={m.id}
                href={`/bilimlar/${m.id}`}
                className="rounded-kartochka border-ramka-yumshoq hover:border-ramka flex flex-col border bg-white/[0.02] p-4 transition-colors"
              >
                <CardTitle>
                  {m.title}
                  {qulf && <span aria-hidden> 🔒</span>}
                </CardTitle>
                {m.description && (
                  <p className="text-matn-past mt-2 text-sm leading-relaxed">
                    {m.description}
                  </p>
                )}
                <p className="text-matn-past mt-auto pt-3 text-xs">
                  {[vaqt, m.toifa].filter(Boolean).join(" · ")}
                </p>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
