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

          {bozor ? (
            <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              <Qator nom={t("kuzatuv.narx")} qiymat={narxMatn(bozor.narx)} />
              <Qator nom={t("kuzatuv.market_cap")} qiymat={pul(bozor.marketCap)} />
              <Qator nom={t("kuzatuv.hajm_24s")} qiymat={pul(bozor.hajm24s)} />
              <Qator nom={t("kuzatuv.soat_1")} qiymat={foiz(bozor.ozgarish1s)} />
              <Qator nom={t("kuzatuv.soat_24")} qiymat={foiz(bozor.ozgarish24s)} />
              <Qator nom={t("kuzatuv.kun_7")} qiymat={foiz(bozor.ozgarish7k)} />
            </div>
          ) : (
            <p className="text-matn-past text-sm">{t("umumiy.yoq")}</p>
          )}

          <p className="text-matn-past mt-4 text-xs">{t("kuzatuv.tavsiya_emas")}</p>
        </Card>
      ) : null}
    </>
  );
}

function Qator({ nom, qiymat }: { nom: string; qiymat: string | null }) {
  return (
    <div>
      <p className="text-matn-past text-[11px]">{nom}</p>
      <p className="tabular-nums">{qiymat ?? "—"}</p>
    </div>
  );
}

function narxMatn(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  return `$${x.toPrecision(6)}`;
}

function pul(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  const birliklar: [number, string][] = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [chegara, belgi] of birliklar) {
    if (Math.abs(x) >= chegara) return `$${(x / chegara).toFixed(2)}${belgi}`;
  }
  return `$${x.toFixed(2)}`;
}

function foiz(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  return `${x > 0 ? "+" : ""}${x.toFixed(2)}%`;
}
