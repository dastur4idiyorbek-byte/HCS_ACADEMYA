import Link from "next/link";

import { Ikonka, type IkonkaNomi } from "@/components/ui/Ikonka";
import { Card, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { davomiylikMatn, oqishVaqti } from "@/lib/akademiya";
import { tarjimon } from "@/lib/i18n";
import {
  davomEttirish,
  ilgarilashlar,
  kontent,
  tarifQamraydi,
  type Kontent,
} from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Akademiya — o'quv bo'limining bosh sahifasi.
 *
 * NEGA ALOHIDA SAHIFA KERAK. Ilgari o'quv qismi ikkiga bo'lingan
 * edi: video darslar va kurs. Ikkalasi ham ro'yxat, boshlanish
 * nuqtasi esa yo'q edi — foydalanuvchi "qayerdan boshlayman?" degan
 * savolga javob topmasdi.
 *
 * Bu sahifa uchta ishni qiladi:
 *
 *   1. Boshlangan darsni tepaga chiqaradi ("Davom ettirish")
 *   2. Uchta bo'limga yo'l ko'rsatadi
 *   3. Har biridan bir nechtasini namuna qilib beradi
 *
 * QULFLASH SERVERDA. Tarifi yetmaydigan darsning NOMI ham
 * ko'rsatiladi (u sotiladigan qiymat), lekin matni va videosi
 * yuborilmaydi.
 */
export default async function Akademiya() {
  const { til, tarif, foydalanuvchi } = await kirim();
  const t = tarjimon(til);

  const hammasi = kontent();
  const videolar = hammasi.filter((k) => k.kind === "video");
  const maqolalar = hammasi.filter((k) => k.kind === "maqola");

  // Kirmagan foydalanuvchi bu yerga yetib kelmaydi (layout tekshiradi),
  // lekin `foydalanuvchi` baribir `null` bo'lishi mumkin — o'shanda
  // ilgarilash bo'sh qoladi va "Davom ettirish" ko'rinmaydi.
  const holatlar = foydalanuvchi
    ? ilgarilashlar(foydalanuvchi.id)
    : new Map<number, { foiz: number }>();
  const davomi = foydalanuvchi ? davomEttirish(foydalanuvchi.id) : null;
  const davomDars =
    davomi === null
      ? null
      : (hammasi.find((k) => k.id === davomi.kontentId) ?? null);

  return (
    <>
      <Sarlavha matn={t("akademiya.sarlavha")} izoh={t("akademiya.izoh")} />

      {/* 1. Davom ettirish — faqat boshlangan dars bo'lsa */}
      {davomDars && davomi && (
        <Card variant="oyna" className="mb-5">
          <p className="text-matn-past text-[11px] tracking-wide uppercase">
            {t("akademiya.davom_bolim")}
          </p>
          <CardTitle className="mt-1">
            {t("akademiya.davom_sarlavha")}
          </CardTitle>

          <div className="mt-4">
            {davomDars.toifa && (
              <p className="text-matn-past text-xs">{davomDars.toifa}</p>
            )}
            <p className="text-sarlavha mt-0.5 font-semibold">
              {davomDars.title}
            </p>

            <div className="mt-3 flex items-center gap-3">
              <div className="bg-panel-yorqin h-2 flex-1 overflow-hidden rounded-full">
                <div
                  className="bg-sarlavha h-full rounded-full"
                  style={{ width: `${davomi.foiz}%` }}
                />
              </div>
              <span className="raqam text-matn-past text-xs">
                {davomi.foiz}%
              </span>
            </div>

            <Link
              href={yoli(davomDars)}
              className="border-ramka rounded-tugma hover:bg-panel-yorqin mt-4 inline-block border px-4 py-2 text-sm transition"
            >
              {t("akademiya.davom_tugma")}
            </Link>
          </div>
        </Card>
      )}

      {/* 2. Uchta bo'lim */}
      <div className="mb-6 grid gap-3 sm:grid-cols-3">
        <BolimTugma
          yol="/video"
          belgi="video"
          nom={t("menyu.video")}
          soni={videolar.length}
          birlik={t("akademiya.dars_soni")}
        />
        <BolimTugma
          yol="/kurs"
          belgi="kurs"
          nom={t("menyu.kurs")}
          soni={null}
          birlik={t("kontent.tez_kunda")}
        />
        <BolimTugma
          yol="/bilimlar"
          belgi="maqolalar"
          nom={t("akademiya.bilimlar")}
          soni={maqolalar.length}
          birlik={t("akademiya.maqola_soni")}
        />
      </div>

      <div className="space-y-6">
        {/* 3. Yangi bilimlar */}
        {maqolalar.length > 0 && (
          <Bolim
            sarlavha={t("akademiya.yangi_bilimlar")}
            barchasi={t("akademiya.barchasi")}
            yol="/bilimlar"
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {maqolalar.slice(0, 6).map((m) => (
                <MaqolaKartochka
                  key={m.id}
                  maqola={m}
                  qulf={!tarifQamraydi(tarif, m.minTier)}
                  daqiqa={t("akademiya.daqiqa")}
                />
              ))}
            </div>
          </Bolim>
        )}

        {/* 4. Video darslar */}
        {videolar.length > 0 && (
          <Bolim
            sarlavha={t("menyu.video")}
            barchasi={t("akademiya.barchasi")}
            yol="/video"
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {videolar.slice(0, 6).map((v) => (
                <VideoKartochka
                  key={v.id}
                  video={v}
                  foiz={holatlar.get(v.id)?.foiz ?? 0}
                  qulf={!tarifQamraydi(tarif, v.minTier)}
                />
              ))}
            </div>
          </Bolim>
        )}

        {videolar.length === 0 && maqolalar.length === 0 && (
          <Card>
            <p className="text-matn-past text-sm">{t("kontent.yoq")}</p>
          </Card>
        )}
      </div>
    </>
  );
}

/** Dars turiga qarab manzil. */
function yoli(dars: Kontent): string {
  return dars.kind === "maqola" ? `/bilimlar/${dars.id}` : "/video";
}

function BolimTugma({
  yol,
  belgi,
  nom,
  soni,
  birlik,
}: {
  yol: string;
  belgi: IkonkaNomi;
  nom: string;
  soni: number | null;
  birlik: string;
}) {
  return (
    <Link
      href={yol}
      className="rounded-kartochka border-ramka-yumshoq hover:border-ramka hover:bg-panel-yorqin flex flex-col items-center gap-1.5 border bg-white/[0.02] p-5 text-center transition-colors"
    >
      <Ikonka nom={belgi} className="text-ramka h-7 w-7" />
      <span className="text-sarlavha font-semibold">{nom}</span>
      <span className="text-matn-past text-xs">
        {soni === null ? birlik : `${soni} ${birlik}`}
      </span>
    </Link>
  );
}

function Bolim({
  sarlavha,
  barchasi,
  yol,
  children,
}: {
  sarlavha: string;
  barchasi: string;
  yol: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-sarlavha text-lg font-bold">{sarlavha}</h2>
        <Link
          href={yol}
          className="text-matn-past hover:text-sarlavha text-sm transition-colors"
        >
          {barchasi} →
        </Link>
      </div>
      {children}
    </section>
  );
}

function MaqolaKartochka({
  maqola,
  qulf,
  daqiqa,
}: {
  maqola: Kontent;
  qulf: boolean;
  daqiqa: string;
}) {
  const vaqt = oqishVaqti(maqola.davomiylik, daqiqa);
  return (
    <Link
      href={`/bilimlar/${maqola.id}`}
      className="rounded-kartochka hover:border-ramka flex flex-col border border-white/10 bg-white/[0.02] p-3.5 transition-colors"
    >
      <p className="text-sarlavha font-semibold">
        {maqola.title}
        {qulf && (
          <Ikonka nom="qulf" className="ml-1 inline h-4 w-4 align-[-3px]" />
        )}
      </p>
      {maqola.description && (
        <p className="text-matn-past mt-1.5 line-clamp-2 text-xs leading-relaxed">
          {maqola.description}
        </p>
      )}
      <p className="text-matn-past mt-auto pt-3 text-[11px]">
        {[vaqt, maqola.toifa].filter(Boolean).join(" · ")}
      </p>
    </Link>
  );
}

function VideoKartochka({
  video,
  foiz,
  qulf,
}: {
  video: Kontent;
  foiz: number;
  qulf: boolean;
}) {
  const uzunlik = davomiylikMatn(video.davomiylik);
  return (
    <Link
      href="/video"
      className="rounded-kartochka hover:border-ramka flex flex-col border border-white/10 bg-white/[0.02] p-3.5 transition-colors"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sarlavha font-semibold">
          {video.title}
          {qulf && (
            <Ikonka nom="qulf" className="ml-1 inline h-4 w-4 align-[-3px]" />
          )}
        </p>
        {uzunlik && (
          <span className="raqam text-matn-past shrink-0 text-xs">
            {uzunlik}
          </span>
        )}
      </div>

      {/* Ilgarilash chizig'i FAQAT boshlangan darsda. Nol foizli
          bo'sh chiziq "boshlangan-u, hech narsa qilinmagan" degan
          noto'g'ri taassurot berardi. */}
      {foiz > 0 && (
        <div className="mt-3 flex items-center gap-2">
          <div className="bg-panel-yorqin h-1.5 flex-1 overflow-hidden rounded-full">
            <div
              className="bg-sarlavha h-full rounded-full"
              style={{ width: `${foiz}%` }}
            />
          </div>
          <span className="raqam text-matn-past text-[11px]">{foiz}%</span>
        </div>
      )}
    </Link>
  );
}
