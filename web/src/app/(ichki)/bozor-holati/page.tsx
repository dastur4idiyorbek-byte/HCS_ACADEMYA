import { CoinKorinishi } from "@/components/CoinKorinishi";
import { SektorBloklari } from "@/components/SektorBloklari";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { coinHolatlari, sektorHolatlari } from "@/lib/bozor-server";
import { qisqaSon } from "@/lib/bozor";
import { HALOL_COINLAR } from "@/lib/coingecko-id";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Bozor holati — sektorlar va coinlar (4-prompt davomi).
 *
 * BIR TOMONLAMA, `/salomatlik` bilan bir xil qoida:
 *
 *     ✅ CoinGecko -> shu sahifa
 *     ❌ shu sahifadagi raqam -> modulga -> signal qaroriga
 *
 * Bu yerdagi hech bir son signal moduliga qaytib kirmaydi. Sahifa
 * bozorni KO'RSATADI, tizimga aytmaydi.
 *
 * NIMA UCHUN FAQAT 80 COIN. Boshqa saytlar hamma coinni ko'rsatadi —
 * qimor, foiz va spirtli ichimlik loyihalarini ham. Bizda esa
 * `docs/HALOL_ROYXAT.md` dagi ro'yxatdan tashqarisi ko'rinmaydi:
 * o'z saytimizda haram loyihaning narxini ko'rsatish mahsulotning
 * o'z va'dasiga zid bo'lardi.
 *
 * SEKTOR FOIZLARI ESA BUTUN BOZORDAN. Bu ataylab shunday va sahifada
 * OCHIQ yozilgan. Loyiha egasining qarori: tanish raqam ko'rsatiladi,
 * lekin nimadan hisoblangani yashirilmaydi.
 */
export default async function BozorHolati() {
  const { til } = await kirim();
  const t = tarjimon(til);

  const [coinlar, sektorlar] = await Promise.all([
    coinHolatlari(HALOL_COINLAR),
    sektorHolatlari(HALOL_COINLAR),
  ]);

  const narxi = coinlar.filter((c) => c.narx !== null);
  const jamiKapital = narxi.reduce((s, c) => s + (c.kapital ?? 0), 0);
  const ortacha =
    narxi.length === 0
      ? null
      : narxi.reduce((s, c) => s + (c.ozgarish24 ?? 0), 0) / narxi.length;

  // Eng ko'p ko'rsatiladigan sektor soni. Hammasi (200 dan ortiq)
  // chiqarilsa xarita o'z ma'nosini yo'qotadi — u "bir qarashda"
  // ko'rish uchun.
  const asosiySektorlar = [...sektorlar]
    .sort((a, b) => (b.kapital ?? 0) - (a.kapital ?? 0))
    .slice(0, 24);

  return (
    <>
      <Sarlavha matn={t("holat.sarlavha")} izoh={t("holat.izoh")} />

      <div className="space-y-5">
        <Card variant="oyna">
          <CardTitle>{t("holat.xulosa")}</CardTitle>
          {narxi.length === 0 ? (
            // Ma'lumot olinmadi — nol ko'rsatilmaydi. "$0.00" raqam
            // bo'lib ko'rinadi, aslida esa bilmaslik.
            <p className="text-matn-past mt-3 text-sm">{t("holat.malumot_yoq")}</p>
          ) : (
            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
              <Raqam
                nom={t("holat.jami_coin")}
                qiymat={`${narxi.length} / ${coinlar.length}`}
              />
              <Raqam
                nom={t("holat.jami_kapital")}
                qiymat={`$${qisqaSon(jamiKapital)}`}
              />
              <Raqam
                nom={t("holat.ortacha24")}
                qiymat={
                  ortacha === null
                    ? "—"
                    : `${ortacha > 0 ? "+" : ""}${ortacha.toFixed(2)}%`
                }
              />
            </dl>
          )}
          <CardHint className="mt-4">{t("holat.halol_ogoh")}</CardHint>
        </Card>

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

        <Card>
          <CardTitle>{t("holat.coinlar")}</CardTitle>
          <CardHint className="mt-1 mb-4">{t("holat.coin_izoh")}</CardHint>
          <CoinKorinishi
            coinlar={coinlar}
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
      <dt className="text-matn-past text-xs">{nom}</dt>
      <dd className="raqam text-sarlavha mt-0.5 text-lg font-semibold">
        {qiymat}
      </dd>
    </div>
  );
}
