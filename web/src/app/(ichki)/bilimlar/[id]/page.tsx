import { notFound } from "next/navigation";

import { OqishKuzatuvi } from "@/components/OqishKuzatuvi";
import { Qulf } from "@/components/ui/Qulf";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { oqishVaqti } from "@/lib/akademiya";
import { env } from "@/lib/env";
import { tarjimon } from "@/lib/i18n";
import { kontent, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Bitta maqola.
 *
 * MATN SERVERDA TO'SILADI. Tarifi yetmasa `body` HTML ga umuman
 * qo'shilmaydi — brauzerga yuborilmaydi. Faqat yashirib qo'yish
 * (`hidden`) yetmasdi: matn sahifa manbasida qolib ketardi va uni
 * ko'rish uchun obuna kerak bo'lmasdi.
 */
export default async function Maqola({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { til, tarif, foydalanuvchi } = await kirim();
  const t = tarjimon(til);

  const raqam = Number(id);
  if (!Number.isInteger(raqam)) notFound();

  const maqola = kontent().find((k) => k.id === raqam && k.kind === "maqola");
  if (!maqola) notFound();

  const vaqt = oqishVaqti(maqola.davomiylik, t("akademiya.daqiqa"));
  const izoh = [vaqt, maqola.toifa].filter(Boolean).join(" · ");

  if (!tarifQamraydi(tarif, maqola.minTier)) {
    return (
      <>
        <Sarlavha matn={maqola.title} izoh={izoh || undefined} />
        <Qulf
          til={til}
          kerakliTarif={maqola.minTier}
          botUsername={env().botUsername}
        />
      </>
    );
  }

  return (
    <>
      <Sarlavha matn={maqola.title} izoh={izoh || undefined} />

      <article className="mx-auto max-w-3xl">
        {maqola.matn === null ? (
          <p className="text-matn-past text-sm">{t("akademiya.matn_yoq")}</p>
        ) : (
          <div className="text-[15px] leading-relaxed whitespace-pre-wrap">
            {maqola.matn}
          </div>
        )}
      </article>

      {/* O'qish holati — foydalanuvchi kirgan bo'lsa. */}
      {foydalanuvchi && <OqishKuzatuvi kontentId={maqola.id} />}
    </>
  );
}
