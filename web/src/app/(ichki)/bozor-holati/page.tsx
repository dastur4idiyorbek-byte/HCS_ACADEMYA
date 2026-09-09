import { BozorTepasi } from "@/components/BozorTepasi";
import { CoinKorinishi } from "@/components/CoinKorinishi";
import { SektorBloklari } from "@/components/SektorBloklari";
import { Terminallar } from "@/components/Terminallar";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { coinHolatlari, globalHolat, sektorHolatlari } from "@/lib/bozor-server";
import { sana } from "@/lib/format";
import { HALOL_COINLAR } from "@/lib/coingecko-id";
import { tarjimon } from "@/lib/i18n";
import { sutkalikOzgarish } from "@/lib/jonli-server";
import { zanjirHolatlari } from "@/lib/queries";
import { kirim } from "@/lib/session";
import { TERMINAL_COINLARI, binanceJuftligi } from "@/lib/terminallar";
import { BLOK_NOMLARI, salomatlikIndeksi, xulosaHisobla } from "@/lib/zanjir";

export const dynamic = "force-dynamic";

/** Bozor holati — bir sahifada butun manzara.
 *
 * TUZILMA (loyiha egasining tartibi):
 *
 *     global qator  ->  Salomatlik indeksi  ->  sektorlar
 *     ->  terminallar  ->  coinlar
 *
 * NEGA BIR SAHIFA. Ilgari bu mavzu uchga bo'lingan edi: salomatlik,
 * bozor holati, terminallar. Uchalasi bitta savolning bo'laklari —
 * "bozor hozir qanday?". Uch sahifaga bo'lingani foydalanuvchini
 * yurishga majbur qilardi va manzarani bo'lib tashlardi.
 *
 * ENG MUHIM QOIDA — BIR TOMONLAMA:
 *
 *     ✅ modul / CoinGecko  ->  shu sahifa
 *     ❌ shu sahifadagi raqam  ->  modulga  ->  signal qaroriga
 *
 * Bu yerdagi hech bir son signal moduliga qaytib kirmaydi. Eski
 * tizimda aynan shu chegara buzilgan edi: Bozor Salomatligi
 * "ko'rsatkich" deb boshlanib, keyin signalni to'sadigan darvozaga
 * aylandi va bir necha hafta davomida strategiya emas, o'sha darvoza
 * o'lchandi.
 *
 * NIMA UCHUN FAQAT 80 COIN. Boshqa saytlar hamma coinni ko'rsatadi —
 * qimor, foiz va spirtli ichimlik loyihalarini ham. Bizda esa
 * `docs/HALOL_ROYXAT.md` dagi ro'yxatdan tashqarisi ko'rinmaydi.
 */
export default async function BozorHolati() {
  const { til } = await kirim();
  const t = tarjimon(til);

  const coinlar = zanjirHolatlari();
  const xulosa = xulosaHisobla(coinlar);
  const indeks = salomatlikIndeksi(xulosa);

  const [bozor, sektorlar, global, sutka] = await Promise.all([
    coinHolatlari(HALOL_COINLAR),
    sektorHolatlari(HALOL_COINLAR),
    globalHolat(),
    sutkalikOzgarish(TERMINAL_COINLARI.map((c) => binanceJuftligi(c))),
  ]);

  const ozgarishlar: Record<string, number> = {};
  for (const coin of TERMINAL_COINLARI) {
    const qator = sutka.find((q) => q.juftlik === binanceJuftligi(coin));
    if (qator) ozgarishlar[coin] = qator.ozgarishPct;
  }

  const narxi = bozor.filter((c) => c.narx !== null);
  const halolKapital = narxi.reduce((s, c) => s + (c.kapital ?? 0), 0);

  // Xaritada eng yirik 24 tasi. Hammasi (200 dan ortiq) chiqarilsa
  // katakchalar ko'rinmas nuqtaga aylanadi va xarita "bir qarashda
  // ko'rish" xususiyatini yo'qotadi.
  const asosiySektorlar = [...sektorlar]
    .sort((a, b) => (b.kapital ?? 0) - (a.kapital ?? 0))
    .slice(0, 24);

  return (
    <>
      <Sarlavha matn={t("holat.sarlavha")} izoh={t("holat.izoh")} />

      <BozorTepasi
        global={global}
        halolKapital={halolKapital}
        halolSoni={narxi.length}
        jamiSoni={bozor.length}
        yorliq={{
          jami_kapital: t("holat.jami_kapital"),
          hajm24: t("holat.hajm24"),
          btc_ulushi: t("holat.btc_ulushi"),
          halol_kapital: t("holat.halol_kapital"),
          bozor_manba: t("holat.bozor_manba"),
          halol_manba: t("holat.halol_manba"),
        }}
      />

      <div className="space-y-5">
        {/* 1. Bozor Salomatligi — loyihaning O'Z ko'rsatkichi. Boshqa
            hech bir saytda yo'q, shuning uchun eng tepada va shisha
            yuzada turadi. */}
        <Card variant="oyna">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>{t("zanjir.indeks")}</CardTitle>
            <Badge tone="neytral">{sana(xulosa.oxirgi)}</Badge>
          </div>

          {indeks === null ? (
            <p className="text-matn-past mt-3 text-sm">{t("zanjir.hali_yoq")}</p>
          ) : (
            <>
              <Shkala qiymat={indeks} />
              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
                <Raqam
                  nom={t("zanjir.tekshirildi")}
                  qiymat={String(xulosa.jami)}
                />
                <Raqam nom={t("zanjir.toliq")} qiymat={String(xulosa.toliq)} />
                <Raqam nom={t("zanjir.signal")} qiymat={String(xulosa.signal)} />
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

        {/* 2. Sektorlar */}
        <Card>
          <CardTitle>{t("holat.sektorlar")}</CardTitle>
          {/* OGOHLANTIRISH ro'yxatdan OLDIN turadi: foydalanuvchi
              raqamni ko'rishdan avval u nimadan hisoblanganini
              bilsin. Pastda tursa, ko'pchilik o'qimasdi. */}
          <CardHint className="mt-1 mb-4">{t("holat.sektor_ogoh")}</CardHint>
          {asosiySektorlar.length === 0 ? (
            <p className="text-matn-past text-sm">{t("holat.malumot_yoq")}</p>
          ) : (
            <SektorBloklari
              sektorlar={asosiySektorlar}
              yorliq={{
                sektor: t("holat.sektor"),
                kapital: t("holat.kapital"),
                ozgarish24: t("holat.ozgarish24"),
              }}
            />
          )}
        </Card>

        {/* 3. Terminallar */}
        <Card>
          <CardTitle>{t("zanjir.terminallar")}</CardTitle>
          <div className="mt-3">
            <Terminallar til={til} ozgarishlar={ozgarishlar} />
          </div>
        </Card>

        {/* 4. Coinlar */}
        <Card>
          <CardTitle>{t("holat.coinlar")}</CardTitle>
          <CardHint className="mt-1 mb-4">{t("holat.coin_izoh")}</CardHint>
          <CoinKorinishi
            coinlar={bozor}
            yorliq={{
              jadval: t("holat.korinish_jadval"),
              kartochka: t("holat.korinish_kartochka"),
              xarita: t("holat.korinish_xarita"),
              coin: t("holat.coin"),
              narx: t("holat.narx"),
              ozgarish24: t("holat.ozgarish24"),
              ozgarish7k: t("holat.ozgarish7k"),
              kapital: t("holat.kapital"),
              hajm: t("holat.hajm"),
              yetti_kun: t("holat.yetti_kun"),
              qidir: t("holat.qidir"),
              topilmadi: t("holat.topilmadi"),
            }}
          />
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
      <p className="raqam text-sarlavha mt-4 text-3xl font-bold">{qiymat}/100</p>
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
