import Image from "next/image";

import { Tarmoqlar } from "@/components/Tarmoqlar";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { boshPostlar, havolalar, type BoshPost } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Bir sahifada nechta post. "Ko'proq yuklash" shundan keyingisini oladi. */
const SAHIFA = 20;

/** Bosh sahifa — XRONOLOGIK OQIM (4-prompt, 1-qism).
 *
 * Ilgari bu statik matn edi: bir marta yozilgan, yangilanmaydigan,
 * "tugaydigan" sahifa. Endi u Telegram kanali kabi oqim — eng yangi
 * post tepada.
 *
 * TANISHTIRUV OQIMNING BIRINCHI POSTLARI. Logotip, tavsif, diniy
 * asos va ijtimoiy tarmoqlar oqimdan CHIQARILMADI — ular doim
 * tepada turadi va pastida xronologik postlar davom etadi (loyiha
 * egasining tanlovi).
 *
 * Ular BAZAGA tushmaydi va admin panelda ko'rinmaydi. Sabab: diniy
 * iqtibosning aniq lafzi bilimdon kishi tasdiqlaguncha placeholder
 * bo'lib turishi SHART. Oddiy postga aylantirsak, uni tasodifan
 * o'chirib yoki tahrirlab yuborish mumkin bo'lardi va o'sha qoida
 * jimgina yo'qolardi.
 *
 * QAYTA KIRGAN foydalanuvchi ham eng yangi postdan boshlaydi —
 * "o'qilmagan xabar" tizimi ATAYLAB yo'q (promptning talabi): bu
 * oddiy veb-sahifa, Telegramning nusxasi emas.
 */
export default async function Bosh({
  searchParams,
}: {
  searchParams: Promise<{ oxirgi?: string }>;
}) {
  const { til } = await kirim();
  const { oxirgi } = await searchParams;
  const t = tarjimon(til);
  const tarmoqlar = havolalar();

  const oxirgiId = Number(oxirgi);
  // Bittasini ORTIQCHA so'raymiz: shundan keyin yana post bormi —
  // ikkinchi so'rovsiz bilinadi.
  const olingan = boshPostlar(
    SAHIFA + 1,
    Number.isInteger(oxirgiId) && oxirgiId > 0 ? oxirgiId : undefined,
  );
  const postlar = olingan.slice(0, SAHIFA);
  const yanaBor = olingan.length > SAHIFA;

  return (
    <div className="space-y-5">
      {/* ---- Oqimning birinchi, doimiy postlari ---- */}
      <header className="flex flex-col items-center py-6 text-center">
        <Image
          src="/logo.jpg"
          alt="HCS — Halol Crypto Savdo"
          width={96}
          height={96}
          className="rounded-kartochka"
          priority
        />
        <h1 className="text-sarlavha mt-4 text-2xl font-bold tracking-wide sm:text-3xl">
          HALOL CRYPTO SAVDO
        </h1>
        <p className="text-matn-past mt-1 text-sm">{t("bosh.shior")}</p>
      </header>

      {/* Oqimning eng tepasidagi kartochka — "oyna" yuzasi shu yerda.
          Quyidagi postlar oddiy qoladi: bir ekranda o'nlab shisha yuza
          effektni ham, telefon tezligini ham yo'qotadi. */}
      <Card variant="oyna">
        <CardTitle>{t("bosh.tavsif_sarlavha")}</CardTitle>
        <p className="mt-2 text-sm leading-relaxed">{t("bosh.tavsif")}</p>
      </Card>

      <div className="grid gap-5 sm:grid-cols-2">
        <Card>
          <CardTitle>{t("bosh.kimga_sarlavha")}</CardTitle>
          <p className="mt-2 text-sm leading-relaxed">{t("bosh.kimga")}</p>
        </Card>

        <Card>
          <CardTitle>{t("bosh.nega_halol_sarlavha")}</CardTitle>
          <p className="mt-2 text-sm leading-relaxed">{t("bosh.nega_halol")}</p>
        </Card>
      </div>

      {/* Diniy asos — matn ATAYLAB yozilmagan.
          Iqtibosning aniq lafzi bilimdon kishi tasdiqlagandan keyin
          kiritiladi. Bu joy dizayn jihatdan tayyor: matn almashtirilsa
          kifoya, boshqa hech narsa o'zgarmaydi. */}
      <Card variant="urgu">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>☪️ {t("bosh.diniy_sarlavha")}</CardTitle>
          <Badge tone="ortacha">{t("bosh.diniy_holat")}</Badge>
        </div>
        <p className="text-matn-past mt-3 text-sm leading-relaxed italic">
          {t("bosh.diniy_placeholder")}
        </p>
        <CardHint className="mt-3">{t("bosh.diniy_izoh")}</CardHint>
      </Card>

      <Tarmoqlar havolalar={tarmoqlar} til={til} />

      {/* ---- Xronologik oqim ---- */}
      <div className="border-ramka-yumshoq border-t pt-5">
        {postlar.length === 0 ? (
          <Card>
            <p className="text-matn-past text-sm">{t("bosh.oqim_yoq")}</p>
          </Card>
        ) : (
          <div className="space-y-5">
            {postlar.map((p) => (
              <PostKartochka key={p.id} post={p} />
            ))}
          </div>
        )}

        {/* "Ko'proq yuklash" — oddiy HAVOLA, JS emas.
            Sabab: sahifa server komponenti va JS o'chiq bo'lsa ham
            ishlashi kerak. Manzilda oxirgi post id si turadi, ya'ni
            havolani ulashish ham mumkin. */}
        {yanaBor && postlar.length > 0 && (
          <div className="mt-6 flex justify-center">
            <a
              href={`/bosh?oxirgi=${postlar[postlar.length - 1].id}`}
              className="border-ramka-yumshoq rounded-tugma hover:bg-panel-yorqin border px-4 py-2 text-sm transition"
            >
              {t("bosh.koproq")}
            </a>
          </div>
        )}
        {!yanaBor && oxirgiId > 0 && (
          <p className="text-matn-past mt-6 text-center text-sm">
            {t("bosh.oqim_oxiri")}
          </p>
        )}
      </div>
    </div>
  );
}

function PostKartochka({ post }: { post: BoshPost }) {
  return (
    <article className="border-ramka-yumshoq bg-panel rounded-kartochka border p-4">
      <p className="text-matn-past text-xs">{sana(post.yaratilgan)}</p>

      {post.matn && (
        <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">
          {post.matn}
        </p>
      )}

      {post.mediaTuri === "image" && post.media && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={`/api/post-media/${post.media}`}
          alt=""
          loading="lazy"
          className="rounded-tugma mt-3 w-full"
        />
      )}

      {post.mediaTuri === "audio" && post.media && (
        <audio
          controls
          preload="none"
          src={`/api/post-media/${post.media}`}
          className="mt-3 w-full"
        />
      )}
    </article>
  );
}
