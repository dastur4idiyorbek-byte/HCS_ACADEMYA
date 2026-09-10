import { BolimTugmalari } from "@/components/BolimTugmalari";
import { BozorTepasi } from "@/components/BozorTepasi";
import { CoinKorinishi } from "@/components/CoinKorinishi";
import { SektorBloklari } from "@/components/SektorBloklari";
import { Blokcheynlar } from "@/components/Blokcheynlar";
import { NarxGrafigi } from "@/components/NarxGrafigi";
import { TarmoqFaolligi } from "@/components/TarmoqFaolligi";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { Sarlavha } from "@/components/ui/Sarlavha";
import {
  blokcheynHolatlari,
  coinHolatlari,
  globalHolat,
  qorquvOchkozlik,
  sektorHolatlari,
  tarmoqFaolliklari,
} from "@/lib/bozor-server";
import { altcoinMavsumi } from "@/lib/bozor";
import { sektorlarniSaralash } from "@/lib/sektorlar";
import { HALOL_COINLAR } from "@/lib/coingecko-id";
import { tarjimon } from "@/lib/i18n";
import { zanjirHolatlari } from "@/lib/queries";
import { kirim } from "@/lib/session";
import {
  BLOK_NOMLARI,
  salomatlikIndeksi,
  salomatlikTasnifi,
  xulosaHisobla,
} from "@/lib/zanjir";

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
  const tasnif = salomatlikTasnifi(indeks);

  const [bozor, sektorlar, global, qorquv, zanjirlar, faollik] =
    await Promise.all([
      coinHolatlari(HALOL_COINLAR),
      sektorHolatlari(HALOL_COINLAR),
      globalHolat(),
      qorquvOchkozlik(),
      blokcheynHolatlari(HALOL_COINLAR),
      tarmoqFaolliklari(HALOL_COINLAR),
    ]);

  const narxi = bozor.filter((c) => c.narx !== null);
  const halolKapital = narxi.reduce((s, c) => s + (c.kapital ?? 0), 0);

  // Faqat QO'LDA tanlangan sektorlar. Sabab `lib/sektorlar.ts` da:
  // CoinGecko toifalarining ko'pi sektor emas ("Made in USA",
  // "CoinList Launchpad") va ular ustma-ust tushadi.
  const asosiySektorlar = sektorlarniSaralash(sektorlar);

  return (
    <>
      <Sarlavha
        matn={t("holat.sarlavha")}
        izoh={t("holat.izoh")}
        belgi="bozor_holati"
      />

      <BolimTugmalari
        bolimlar={[
          {
            langar: "salomatlik",
            nom: t("holat.bolim_salomatlik"),
            belgi: "salomatlik",
          },
          {
            langar: "sektorlar",
            nom: t("holat.bolim_sektorlar"),
            belgi: "sektorlar",
          },
          {
            langar: "blokcheynlar",
            nom: t("holat.bolim_blokcheynlar"),
            belgi: "blokcheyn",
          },
          {
            langar: "onchain",
            nom: t("holat.bolim_onchain"),
            belgi: "onchain",
          },
          { langar: "grafik", nom: t("holat.bolim_grafik"), belgi: "grafik" },
          {
            langar: "coinlar",
            nom: t("holat.bolim_coinlar"),
            belgi: "coinlar",
          },
        ]}
      />

      <BozorTepasi
        salomatlik={indeks}
        salomatlikTasnifi={
          tasnif === null ? undefined : t(`zanjir.tasnif_${tasnif}`)
        }
        global={global}
        qorquv={qorquv}
        altcoin={altcoinMavsumi(bozor)}
        halolKapital={halolKapital}
        halolSoni={narxi.length}
        jamiSoni={bozor.length}
        yorliq={{
          salomatlik: t("zanjir.indeks"),
          jami_kapital: t("holat.jami_kapital"),
          hajm24: t("holat.hajm24"),
          btc_ulushi: t("holat.btc_ulushi"),
          eth_ulushi: t("holat.eth_ulushi"),
          qorquv: t("holat.qorquv"),
          altcoin: t("holat.altcoin"),
          halol_kapital: t("holat.halol_kapital"),
          bozor_manba: t("holat.bozor_manba"),
          halol_manba: t("holat.halol_manba"),
        }}
      />

      <div className="space-y-5">
        <div id="salomatlik" className="scroll-mt-20" />
        {/* 1. Salomatlik TAFSILOTI. Indeks raqamining o'zi tepadagi
            doirada turadi — bu yerda takrorlanmaydi. Qoladigan narsa:
            nechta coin tekshirildi va zanjir qayerda uzildi. */}
        {indeks !== null && (
          <Card>
            <CardTitle className="flex items-center gap-2">
              <Ikonka nom="salomatlik" />
              {t("zanjir.tafsilot")}
            </CardTitle>
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
            <CardHint className="mt-4">{t("zanjir.bir_tomonlama")}</CardHint>
          </Card>
        )}

        {indeks === null && (
          <Card>
            <p className="text-matn-past text-sm">{t("zanjir.hali_yoq")}</p>
          </Card>
        )}

        {Object.keys(xulosa.uzilishlar).length > 0 && (
          <Card>
            <CardTitle className="flex items-center gap-2">
              <Ikonka nom="zanjir" />
              {t("zanjir.uzilish_joylari")}
            </CardTitle>
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
        <Card id="sektorlar" className="scroll-mt-20">
          <CardTitle className="flex items-center gap-2">
            <Ikonka nom="sektorlar" />
            {t("holat.sektorlar")}
          </CardTitle>
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

        {/* 3. Blokcheynlar — TVL. Coinlar jadvalidagi kapital bilan
            takrorlanmaydi: bu narxdan mustaqil ko'rsatkich. */}
        {zanjirlar.length > 0 && (
          <Card id="blokcheynlar" className="scroll-mt-20">
            <CardTitle className="flex items-center gap-2">
              <Ikonka nom="blokcheyn" />
              {t("holat.blokcheynlar")}
            </CardTitle>
            <CardHint className="mt-1 mb-4">
              {t("holat.blokcheyn_izoh")}
            </CardHint>
            <Blokcheynlar
              zanjirlar={zanjirlar}
              coinlar={bozor}
              yorliq={{ tvl: t("holat.tvl") }}
            />
          </Card>
        )}

        {/* 4. On-chain — tarmoq faolligi. Narx savdodan keladi, bu
            raqamlar tarmoqning O'ZIDAN: coin haqiqatan
            ishlatilyaptimi degan boshqa savolga javob beradi. */}
        {faollik.length > 0 && (
          <Card id="onchain" className="scroll-mt-20">
            <CardTitle className="flex items-center gap-2">
              <Ikonka nom="onchain" />
              {t("holat.onchain")}
            </CardTitle>
            <CardHint className="mt-1 mb-4">{t("holat.onchain_izoh")}</CardHint>
            <TarmoqFaolligi
              tarmoqlar={faollik}
              coinlar={bozor}
              yorliq={{
                tarmoq: t("holat.tarmoq"),
                tranzaksiya: t("holat.tranzaksiya"),
                blok: t("holat.blok"),
                komissiya: t("holat.komissiya"),
              }}
            />
          </Card>
        )}

        {/* 5. Real narx grafigi. Ilgari bu yerda coin "chiplari"
            ro'yxati turardi va grafik faqat bosilganda ochilardi —
            foydalanuvchi uni ko'rmasdi. Endi grafik darrov turadi. */}
        <Card id="grafik" className="scroll-mt-20">
          <CardTitle className="flex items-center gap-2">
            <Ikonka nom="grafik" />
            {t("holat.grafik")}
          </CardTitle>
          <div className="mt-3">
            <NarxGrafigi
              coinlar={bozor}
              xatoMatni={t("signal.grafik_xato")}
              qidirMatni={t("holat.qidir")}
            />
          </div>
        </Card>

        {/* 4. Coinlar */}
        <Card id="coinlar" className="scroll-mt-20">
          <CardTitle className="flex items-center gap-2">
            <Ikonka nom="coinlar" />
            {t("holat.coinlar")}
          </CardTitle>
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

function Raqam({ nom, qiymat }: { nom: string; qiymat: string }) {
  return (
    <div>
      <dt className="text-matn-past text-xs uppercase">{nom}</dt>
      <dd className="raqam text-sarlavha text-lg font-bold">{qiymat}</dd>
    </div>
  );
}
