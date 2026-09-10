import Image from "next/image";

import { Tarmoqlar } from "@/components/Tarmoqlar";
import { Vidjet, type VidjetMalumoti } from "@/components/Vidjetlar";
import { VidjetSozlash } from "@/components/VidjetSozlash";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import {
  avtomatikPostlarniYangila,
  signalgaAloqador,
} from "@/lib/avtomatik-post";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import {
  boshPostlar,
  havolalar,
  kontent,
  pozitsiyalar,
  signallar,
  tarifQamraydi,
  vidjetTanlovi,
  zanjirHolatlari,
  type BoshPost,
} from "@/lib/queries";
import { globalHolat, qorquvOchkozlik } from "@/lib/bozor-server";
import { kirim } from "@/lib/session";
import { korinadiganVidjetlar, type VidjetKod } from "@/lib/vidjetlar";
import {
  salomatlikIndeksi,
  salomatlikTasnifi,
  xulosaHisobla,
} from "@/lib/zanjir";

export const dynamic = "force-dynamic";

/** Bir sahifada nechta post. "Ko'proq yuklash" shundan keyingisini oladi. */
const SAHIFA = 20;

/** Bosh sahifa — XRONOLOGIK OQIM (4-prompt, 1-qism).
 *
 * Ilgari bu statik matn edi: bir marta yozilgan, yangilanmaydigan,
 * "tugaydigan" sahifa. Endi u Telegram kanali kabi oqim — eng yangi
 * post tepada.
 *
 * LOGOTIP ENG TEPADA — loyiha egasining talabi: sahifa bizning
 * belgimiz bilan boshlanadi.
 *
 * TANISHTIRUV MATNI esa oqimdan CHIQARILMADI, lekin pastga ko'chdi:
 * tavsif, diniy asos va ijtimoiy tarmoqlar oqim oxirida turadi
 * (loyiha egasining tanlovi).
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
  const { til, tarif, foydalanuvchi } = await kirim();
  const { oxirgi } = await searchParams;
  const t = tarjimon(til);
  const tarmoqlar = havolalar();

  // --- Vidjetlar uchun ma'lumot ---
  //
  // Hammasi PARALLEL olinadi: ketma-ket bo'lsa sahifa eng sekin
  // manbaning vaqtini kutardi.
  const [global, qorquv] = await Promise.all([
    globalHolat(),
    qorquvOchkozlik(),
  ]);

  const zanjir = xulosaHisobla(zanjirHolatlari());
  const indeks = salomatlikIndeksi(zanjir);
  const tasnif = salomatlikTasnifi(indeks);

  const oxirgiSignallar = signallar(1);
  const mening = foydalanuvchi ? pozitsiyalar(foydalanuvchi.id) : [];
  const ochiq = mening.filter((p) => p.closedAt === null);
  const yopilgan = mening.filter((p) => p.pnlUsd !== null);

  const darslar = kontent();
  const oxirgiDars = darslar.length > 0 ? darslar[darslar.length - 1] : null;

  const vidjetMalumoti: VidjetMalumoti = {
    salomatlik: indeks,
    salomatlikTasnifi: tasnif === null ? null : t(`zanjir.tasnif_${tasnif}`),
    qorquv,
    altcoin: null,
    bozorKapitali: global?.jamiKapital ?? null,
    bozorOzgarish: global?.ozgarish24 ?? null,
    oxirgiSignal:
      oxirgiSignallar.length === 0
        ? null
        : {
            id: oxirgiSignallar[0].id,
            coin: oxirgiSignallar[0].symbol,
            holat: t(`holat.${oxirgiSignallar[0].status}`),
          },
    ochiqPozitsiya: ochiq.length,
    // Yopilgan savdo bo'lmasa `null` — nol emas. "$0.00" "hech narsa
    // yutmadingiz" degan MA'LUMOT bo'lardi, aslida savdo yo'q.
    natijaUsd:
      yopilgan.length === 0
        ? null
        : yopilgan.reduce((s, p) => s + (p.pnlUsd ?? 0), 0),
    tarif: tarif ? tarif.toUpperCase() : null,
    yangiDars:
      oxirgiDars === null
        ? null
        : { id: oxirgiDars.id, nom: oxirgiDars.title, turi: oxirgiDars.kind },
  };

  const tanlov = foydalanuvchi
    ? (vidjetTanlovi(foydalanuvchi.id) as VidjetKod[])
    : [];
  const vidjetlar = korinadiganVidjetlar(tanlov);
  const vidjetNomlari = Object.fromEntries(
    vidjetlar.map((v) => [v.kod, t(v.kalit)]),
  );

  // Signal va haftalik hisobot postlari SHU YERDA tug'iladi.
  //
  // Ular yozuvchidan emas, BAZADAN olinadi: "tarqatilgan, lekin posti
  // yo'q signal bormi?" Sabab `lib/avtomatik-post.ts` da — signalni
  // ham sayt, ham bot (Python) yozadi va ikkala yo'lga chaqiruv
  // qo'ysak, bir mantiqning ikki nusxasi paydo bo'lardi.
  //
  // O'qishdan OLDIN chaqiriladi: shu ochilishda yozilgan post shu
  // ochilishdayoq ko'rinsin.
  //
  // Faqat BIRINCHI sahifada. "Ko'proq yuklash" bosilganda eskiroq
  // postlar so'raladi — o'sha payt yangi post yozish oqimning
  // tepasini o'zgartirardi va foydalanuvchi buni ko'rmasdi ham.
  if (!oxirgi) avtomatikPostlarniYangila();

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
    // Matn oqimi TOR qoladi: umumiy kenglik boshqaruv paneli uchun
    // kengaytirildi, uzun matn qatori esa o'qishni qiyinlashtiradi.
    <div className="mx-auto max-w-3xl space-y-5">
      {/* ---- LOGOTIP — eng tepada ----
          Loyiha egasining talabi: sahifa bizning belgimiz bilan
          boshlanadi. Ilgari u oqimning oxirida turardi va qayta
          kirgan odam uni umuman ko'rmasdi.

          Tanishtiruv MATNI esa pastda qoldi: har safar kirgan odamga
          "biz kimmiz" ni qayta o'qitish shart emas, lekin belgi —
          sahifa kimniki ekanini bir qarashda aytadi. */}
      <header className="flex flex-col items-center pt-2 pb-4 text-center">
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

      {/* ---- 1-QATLAM: SIZ va BUGUN ---- */}
      {/* NEGA TANISHTIRUV EMAS. Ilgari sahifa logotipdan keyin
          to'rtta tanishtiruv kartochkasi bilan davom etardi. Birinchi tashrifda
          bu to'g'ri, ellikinchisida esa to'siq: har safar kirgan odam
          ular ustidan o'tib, keyin yangilikka yetardi.

          Endi tepada BUGUNGI HOLAT turadi, tanishtiruv esa oqimning
          oxiriga ko'chdi — u yerda ham ko'rinadi, chunki yangi odamda
          oqim bo'sh bo'ladi. */}
      <div className="mb-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sarlavha text-lg font-bold">
            {t("vidjet.bolim")}
          </h2>
          {foydalanuvchi && (
            <VidjetSozlash
              boshlangich={vidjetlar.map((v) => v.kod)}
              vidjetNomlari={vidjetNomlari}
              yorliq={{
                sozlash: t("vidjet.sozlash"),
                saqlash: t("vidjet.saqlash"),
                bekor: t("vidjet.bekor"),
                tanlangan: t("vidjet.tanlangan"),
                mavjud: t("vidjet.mavjud"),
                saqlandi: t("vidjet.saqlandi"),
                xato: t("vidjet.xato"),
              }}
            />
          )}
        </div>

        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
          {vidjetlar.map((v) => (
            <Vidjet
              key={v.kod}
              kod={v.kod}
              nom={t(v.kalit)}
              malumot={vidjetMalumoti}
              qulf={v.talab !== null && !tarifQamraydi(tarif, v.talab)}
              yorliq={{
                qulf: t("vidjet.qulf"),
                yoq: t("vidjet.yoq"),
                signal_yoq: t("vidjet.signal_yoq"),
                dona: t("vidjet.dona"),
                tarif_yoq: t("profil.yoq"),
                halol_manba: t("holat.halol_manba"),
              }}
            />
          ))}
        </div>
      </div>

      {/* ---- Xronologik oqim ---- */}
      <div className="border-ramka-yumshoq border-t pt-5">
        {postlar.length === 0 ? (
          <Card>
            <p className="text-matn-past text-sm">{t("bosh.oqim_yoq")}</p>
          </Card>
        ) : (
          <div className="space-y-5">
            {postlar.map((p) => (
              <PostKartochka
                key={p.id}
                post={p}
                obunachi={tarifQamraydi(tarif, "lite")}
                yorliq={{
                  ochish: t("bosh.ochish"),
                  signal: t("bosh.signal_belgi"),
                  qulf: t("bosh.signal_qulf"),
                  obuna: t("bosh.signal_obuna"),
                  signalOchish: t("bosh.signal_ochish"),
                }}
              />
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

      {/* ---- 3-QATLAM: loyiha haqida ----
          Oqimning OXIRIDA. Yangi odamda oqim bo'sh bo'ladi va u
          baribir shu yerga darrov yetadi; qayta kirgan odam esa
          har safar ular ustidan o'tishga majbur emas. */}
      <div className="border-ramka-yumshoq space-y-5 border-t pt-8">
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
            <p className="mt-2 text-sm leading-relaxed">
              {t("bosh.nega_halol")}
            </p>
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
      </div>
    </div>
  );
}

/** Avtomatik post turiga qarab belgi. Qo'lda yozilganda belgi yo'q. */
const MANBA_BELGISI: Record<string, string> = {
  dars: "🎬",
  maqola: "📄",
  signal: "🔒📈",
  tp1: "🔒🎯",
  tp2: "🔒🏁",
  hisobot: "📊",
};

function PostKartochka({
  post,
  obunachi,
  yorliq,
}: {
  post: BoshPost;
  obunachi: boolean;
  yorliq: {
    ochish: string;
    signal: string;
    qulf: string;
    obuna: string;
    signalOchish: string;
  };
}) {
  const belgi = MANBA_BELGISI[post.manbaTuri];
  // Signalga aloqador postlar QULF ortida. Ro'yxat `avtomatik-post.ts`
  // da — bu yerda takrorlanmaydi, aks holda yangi tur qo'shilganda
  // qulflangan xabar ochiq post kabi ko'rinardi.
  const qulf = signalgaAloqador(post.manbaTuri);
  return (
    <article className="border-ramka-yumshoq bg-panel rounded-kartochka border p-4">
      <p className="text-matn-past flex flex-wrap items-center gap-2 text-xs">
        {belgi && (
          <span aria-hidden className="text-sm">
            {belgi}
          </span>
        )}
        {/* Qulf yorlig'i MATN bilan. Faqat ikonka qo'yilsa, uning
            ma'nosini har kim o'zicha tushunardi. */}
        {qulf && (
          <span className="border-ramka rounded-tugma border px-2 py-0.5 font-semibold">
            {yorliq.signal}
          </span>
        )}
        <span>{sana(post.yaratilgan)}</span>
      </p>

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

      {/* Avtomatik postning tugmasi. Qulflangan darsga olib borsa
          ham YASHIRILMAYDI: bosilganda qulf ekrani chiqadi va odam
          nima yetishmayotganini biladi. Saytning qolgan qismida ham
          shu qoida — dars nomi sotiladigan qiymat.

          SIGNAL POSTIDA tugma foydalanuvchiga QARAB o'zgaradi.
          Obunachi signalning o'ziga o'tadi; obunasi yo'q odam esa
          tarif sahifasiga — signal sahifasi unga baribir ochilmaydi
          va "ochish" tugmasi bo'sh va'da bo'lardi.

          Post MATNI bazada bitta tilda yozilgan, bu chaqiriq esa
          har foydalanuvchi uchun alohida chiziladi va tarjima
          qilinadi. */}
      {qulf && !obunachi && (
        <p className="text-matn-past mt-2 text-sm">{yorliq.qulf}</p>
      )}

      {post.havola && (
        <a
          href={qulf && !obunachi ? "/profil" : post.havola}
          className="border-ramka rounded-tugma hover:bg-panel-yorqin mt-3 inline-block border px-4 py-2 text-sm transition"
        >
          {qulf
            ? obunachi
              ? yorliq.signalOchish
              : yorliq.obuna
            : yorliq.ochish}{" "}
          →
        </a>
      )}
    </article>
  );
}
