import { BozorKesimi } from "@/components/kuzatuv/BozorKesimi";
import { Card } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { kuzatuvBozori, kuzatuvCoin, qidiruvHolati, qidiruvIshlat } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Coin qidirish — oddiy foydalanuvchi uchun (7-qism).
 *
 * NIMA KO'RSATILADI: narx, kapitalizatsiya, hajm, o'zgarish va
 * struktura holati — oddiy, umumiy shaklda.
 *
 * NIMA KO'RSATILMAYDI (faqat admin uchun qoladi): stakan, savdo
 * lentasi, xarid bosimi, yirik operatsiyalar, zona konfluensiyasi
 * tafsiloti, Liquidity Sweep va RSI tafsiloti.
 *
 * FAQAT TOP 20. Coin ro'yxatda bo'lmasa — ochiq, tushunarli xabar.
 * "Diqqatga molik +10" ham bunga KIRMAYDI: u admin uchun.
 *
 * CHEGARA HISOBGA OLINADI FAQAT TOPILGAN QIDIRUVDA. Foydalanuvchi
 * mavjud bo'lmagan coin nomini yozib, kunlik limitini yo'qotmasin.
 */
export default async function QidiruvSahifasi({
  searchParams,
}: {
  searchParams: Promise<{ coin?: string }>;
}) {
  const { coin: sorov } = await searchParams;
  const { foydalanuvchi, tarif, til } = await kirim();
  const t = tarjimon(til);

  const nom = (sorov ?? "").trim().toUpperCase();
  const yaroqli = /^[A-Z0-9]{1,15}$/.test(nom);

  let holat = foydalanuvchi ? qidiruvHolati(foydalanuvchi.id, tarif) : null;
  let coin = null;
  let bozor = null;

  if (yaroqli && foydalanuvchi) {
    const topilgan = kuzatuvCoin(nom);
    // FAQAT Top 20 — "+10" admin uchun (7-qism).
    if (topilgan && topilgan.royxat === "top") {
      // Chegara AYNAN shu yerda ishlatiladi: coin topilgan va
      // ma'lumot beriladigan holatda. Topilmagan qidiruv limitni
      // yemaydi.
      holat = qidiruvIshlat(foydalanuvchi.id, tarif);
      if (holat.mumkin) {
        coin = topilgan;
        bozor = kuzatuvBozori(nom);
      }
    }
  }

  return (
    <>
      <Sarlavha matn={t("kuzatuv.qidiruv.sarlavha")} belgi="qidiruv" />

      <Card className="mb-4">
        <p className="text-matn-past mb-3 text-sm">{t("kuzatuv.qidiruv.tavsif")}</p>
        <form method="get" className="flex flex-wrap gap-2">
          <input
            type="text"
            name="coin"
            defaultValue={nom}
            maxLength={15}
            placeholder={t("kuzatuv.qidiruv.maydon")}
            aria-label={t("kuzatuv.qidiruv.maydon")}
            className="rounded-tugma border-ramka-yumshoq bg-fon focus:border-ramka min-w-40 flex-1 border px-3 py-2 text-sm outline-none"
          />
          <button
            type="submit"
            className="rounded-tugma bg-ramka px-4 py-2 text-sm font-medium text-[#0a2450] hover:brightness-110"
          >
            {t("kuzatuv.qidiruv.tugma")}
          </button>
        </form>

        {holat ? (
          <p className="text-matn-past mt-2 text-xs">
            {holat.mumkin
              ? t("kuzatuv.qidiruv.qoldi").replace("{son}", String(holat.qoldi))
              : t("kuzatuv.qidiruv.chegara")}
            {tarif !== "premium" ? ` ${t("kuzatuv.qidiruv.obuna_kopaytiradi")}` : ""}
          </p>
        ) : null}
      </Card>

      {nom && !coin ? (
        <Card>
          <p className="text-matn-past flex items-start gap-2 text-sm">
            <Ikonka nom="malumot" className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {holat && !holat.mumkin
                ? t("kuzatuv.qidiruv.chegara")
                : t("kuzatuv.qidiruv.topilmadi")}
            </span>
          </p>
        </Card>
      ) : null}

      {coin ? (
        <Card>
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="text-sarlavha text-lg font-semibold">{coin.symbol}/USDT</p>
            <span className="text-matn-past text-sm">
              {t(`kuzatuv.yonalish.${coin.yonalish}`)}
            </span>
          </div>

          {/* CHEGARA: `toliq` BERILMAYDI — FDV, ta'minot va tarixiy
              chekkalar faqat adminda qoladi (7-qism). */}
        </Card>
      ) : null}

      {coin && bozor ? (
        <>
          <BozorKesimi bozor={bozor} t={t} />
          <p className="text-matn-past mt-2 text-xs">{t("kuzatuv.tavsiya_emas")}</p>
        </>
      ) : null}
    </>
  );
}

