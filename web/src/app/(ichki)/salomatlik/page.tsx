import { Terminallar } from "@/components/Terminallar";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { sutkalikOzgarish } from "@/lib/jonli-server";
import { zanjirHolatlari } from "@/lib/queries";
import { kirim } from "@/lib/session";
import { TERMINAL_COINLARI, binanceJuftligi } from "@/lib/terminallar";
import { BLOK_NOMLARI, salomatlikIndeksi, xulosaHisobla } from "@/lib/zanjir";

export const dynamic = "force-dynamic";

/** Bozor Salomatligi — FAQAT KO'RSATISH (4-prompt, 2-qism).
 *
 * ENG MUHIM QOIDA, QAT'IY:
 *
 *     ✅ modul -> hisoblaydi -> shu sahifa (bir tomonlama)
 *     ❌ shu sahifadagi qiymat -> modulga qaytib -> signal qaroriga
 *        ta'sir qiladi (TAQIQLANADI)
 *
 * Bu indeks modulning ICHKI mantig'iga KIRISH sifatida
 * ishlatilmaydi. U — modul ishini TASHQARIDAN kuzatish uchun
 * interfeys, boshqa hech narsa.
 *
 * Nima uchun bu shunchalik qat'iy yozilgan: eski tizimda aynan shu
 * chegara buzilgan edi. Bozor Salomatligi "ko'rsatkich" deb
 * boshlanib, keyin signal chiqishini to'sadigan darvozaga aylandi.
 * Natijada modul o'zining ko'rsatkichiga qarab qaror qiladigan,
 * tekshirib bo'lmaydigan halqa paydo bo'ldi — va bir necha hafta
 * davomida strategiya emas, o'sha darvoza o'lchandi.
 *
 * INDEKS NIMANI ANGLATADI: o'rtacha nechta blok bog'langani (0-4)
 * foizga aylantirilgani. Sof statistik ko'rsatkich — modul
 * birligining o'zida o'lchanadi, o'ylab topilgan formula emas.
 */
export default async function Salomatlik() {
  const { til } = await kirim();
  const t = tarjimon(til);

  const coinlar = zanjirHolatlari();
  const xulosa = xulosaHisobla(coinlar);
  const indeks = salomatlikIndeksi(xulosa);

  // Narx olinmasa foiz KO'RSATILMAYDI — nol deb ko'rsatish
  // "o'zgarmadi" degan ma'lumot bo'lardi, aslida "bilmaymiz".
  const sutka = await sutkalikOzgarish(
    TERMINAL_COINLARI.map((c) => binanceJuftligi(c)),
  );
  const ozgarishlar: Record<string, number> = {};
  for (const coin of TERMINAL_COINLARI) {
    const qator = sutka.find((q) => q.juftlik === binanceJuftligi(coin));
    if (qator) ozgarishlar[coin] = qator.ozgarishPct;
  }

  return (
    <>
      <Sarlavha matn={t("menyu.salomatlik")} izoh={t("zanjir.indeks_izoh")} />

      <div className="space-y-5">
        {/* Sahifaning asosiy kartochkasi — shu yerda "oyna" yuzasi
            ishlatiladi. Bozor Salomatligi loyihaning o'z ko'rsatkichi
            va sahifadagi eng muhim blok. */}
        <Card variant="oyna">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>{t("zanjir.indeks")}</CardTitle>
            <Badge tone="neytral">{sana(xulosa.oxirgi)}</Badge>
          </div>

          {indeks === null ? (
            <p className="text-matn-past mt-3 text-sm">
              {t("zanjir.hali_yoq")}
            </p>
          ) : (
            <>
              <Shkala qiymat={indeks} />
              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
                <Raqam
                  nom={t("zanjir.tekshirildi")}
                  qiymat={String(xulosa.jami)}
                />
                <Raqam nom={t("zanjir.toliq")} qiymat={String(xulosa.toliq)} />
                <Raqam
                  nom={t("zanjir.signal")}
                  qiymat={String(xulosa.signal)}
                />
                <Raqam
                  nom={t("zanjir.ortacha")}
                  qiymat={`${xulosa.ortachaBloklar.toFixed(1)} / ${BLOK_NOMLARI.length}`}
                />
              </dl>
            </>
          )}

          <CardHint className="mt-4">{t("zanjir.bir_tomonlama")}</CardHint>
        </Card>

        {Object.keys(xulosa.uzilishlar).length > 0 && (
          <Card>
            <CardTitle>{t("zanjir.uzilish_joylari")}</CardTitle>
            <ul className="mt-3 space-y-1.5 text-sm">
              {Object.entries(xulosa.uzilishlar)
                .sort((a, b) => b[1] - a[1])
                .map(([blok, soni]) => (
                  <li
                    key={blok}
                    className="flex items-center justify-between gap-3"
                  >
                    <span>{blok}</span>
                    <span className="raqam text-matn-past">{soni}</span>
                  </li>
                ))}
            </ul>
          </Card>
        )}

        <Card>
          <CardTitle>{t("zanjir.terminallar")}</CardTitle>
          <div className="mt-3">
            <Terminallar til={til} ozgarishlar={ozgarishlar} />
          </div>
        </Card>
      </div>
    </>
  );
}

/** Qizil-sariq-yashil shkala va joriy qiymat ustidagi strelka. */
function Shkala({ qiymat }: { qiymat: number }) {
  const joy = Math.min(100, Math.max(0, qiymat));
  return (
    <div className="mt-4">
      <div className="relative">
        <div
          className="h-3 w-full rounded-full"
          style={{
            background:
              "linear-gradient(to right, var(--rang-past-toq), var(--rang-ortacha), var(--rang-yaxshi))",
          }}
        />
        {/* Strelka — mutlaq joylashuv, chunki qiymat 0-100 oralig'ida
            uzluksiz siljiydi. */}
        <div
          aria-hidden
          className="absolute -top-1.5 -translate-x-1/2"
          style={{ left: `${joy}%` }}
        >
          <div className="border-sarlavha bg-fon h-6 w-1.5 rounded-full border" />
        </div>
      </div>
      <p className="raqam text-sarlavha mt-4 text-3xl font-bold">
        {qiymat}/100
      </p>
    </div>
  );
}

function Raqam({ nom, qiymat }: { nom: string; qiymat: string }) {
  return (
    <div>
      <dt className="text-matn-past text-xs uppercase">{nom}</dt>
      <dd className="raqam text-sarlavha text-lg font-bold">{qiymat}</dd>
    </div>
  );
}
