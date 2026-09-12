import { CoinQatori } from "@/components/kuzatuv/CoinQatori";
import { Card } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { kuzatuvCoinlari, kuzatuvSkani } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { YangilashTugmasi } from "./YangilashTugmasi";

export const dynamic = "force-dynamic";

/** Kuzatuv paneli — 80 coin, FAQAT ADMIN uchun (9-prompt).
 *
 * IKKI DARAJALI RO'YXAT (5.1-qism):
 *   🟢 Top 20      — yuqorida, to'liq o'lchamda
 *   🟡 +10 kuzatuvda — pastroqda, kichikroq va xiraroq
 *
 * QAT'IY CHEGARA: bu sahifada Entry, Stop yoki TP raqami YO'Q.
 * Sahifa ma'lumot beradi, tavsiya bermaydi — buni sahifaning
 * o'zi ham ochiq yozadi.
 *
 * BO'SH RO'YXAT — XATO EMAS. Bozor tushayotganda xarid nomzodi
 * bo'lmasligi kerak, va sahifa buni shunday tushuntiradi. Ro'yxat
 * sun'iy to'ldirilmaydi.
 */
export default async function KuzatuvSahifasi() {
  const { admin, til } = await kirim();
  const t = tarjimon(til);

  if (!admin) {
    return (
      <>
        <Sarlavha matn={t("kuzatuv.sarlavha")} belgi="korish" />
        <Card>
          <p className="text-past text-sm">{t("admin.faqat_admin")}</p>
        </Card>
      </>
    );
  }

  const top = kuzatuvCoinlari("top");
  const kuzatuvda = kuzatuvCoinlari("kuzatuvda");
  const skan = kuzatuvSkani();
  const bosh = top.length === 0 && kuzatuvda.length === 0;

  return (
    <>
      <Sarlavha matn={t("kuzatuv.sarlavha")} belgi="korish" />

      <Card className="mb-4">
        <p className="text-matn-past text-sm">{t("kuzatuv.tavsif")}</p>
      </Card>

      <Card className="mb-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1 text-sm">
            <p className="flex items-center gap-2">
              <span
                className={
                  skan.holat === "xato"
                    ? "text-past"
                    : skan.holat === "yurmoqda"
                      ? "text-ortacha"
                      : "text-yaxshi"
                }
              >
                ●
              </span>
              {t(`kuzatuv.holat.${skan.holat}`)}
            </p>
            {skan.holat === "xato" && skan.izoh ? (
              <p className="text-past text-xs">{skan.izoh}</p>
            ) : null}
            <p className="text-matn-past text-xs">
              {t("kuzatuv.tekshirildi")}: {skan.tekshirildi} · {t("kuzatuv.royxatda")}:{" "}
              {skan.otdi}
            </p>
            {skan.tugadi ? (
              <p className="text-matn-past text-xs">
                {t("kuzatuv.oxirgi")}: {skan.tugadi}
              </p>
            ) : null}
          </div>
          <YangilashTugmasi
            matn={t("kuzatuv.yangila")}
            sorandi={t("kuzatuv.yangila_sorandi")}
            izoh={t("kuzatuv.yangila_izoh")}
          />
        </div>
      </Card>

      {bosh ? (
        <Card>
          <p className="text-matn text-sm font-semibold">
            {skan.holat === "bosh" ? t("kuzatuv.skan_yoq") : t("kuzatuv.bosh")}
          </p>
          {skan.holat !== "bosh" ? (
            <p className="text-matn-past mt-1.5 text-xs">{t("kuzatuv.bosh_izoh")}</p>
          ) : null}
        </Card>
      ) : null}

      {top.length > 0 ? (
        <section className="mb-6">
          <h2 className="text-sarlavha mb-1 flex items-center gap-2 text-sm font-semibold">
            <Ikonka nom="tasdiq" className="text-yaxshi h-4 w-4" />
            {t("kuzatuv.top")}
            <span className="text-matn-past font-normal">({top.length})</span>
          </h2>
          <p className="text-matn-past mb-3 text-xs">{t("kuzatuv.top_izoh")}</p>
          <div className="space-y-2">
            {top.map((coin) => (
              <CoinQatori key={coin.symbol} coin={coin} t={t} />
            ))}
          </div>
        </section>
      ) : null}

      {kuzatuvda.length > 0 ? (
        <section className="mb-6">
          <h2 className="text-matn-past mb-1 flex items-center gap-2 text-sm font-semibold">
            <Ikonka nom="kutilmoqda" className="text-ortacha h-4 w-4" />
            {t("kuzatuv.kuzatuvda")}
            <span className="font-normal">({kuzatuvda.length})</span>
          </h2>
          <p className="text-matn-past mb-3 text-xs">{t("kuzatuv.kuzatuvda_izoh")}</p>
          <div className="space-y-1.5">
            {kuzatuvda.map((coin) => (
              <CoinQatori key={coin.symbol} coin={coin} t={t} kichik />
            ))}
          </div>
        </section>
      ) : null}

      <p className="text-matn-past mt-6 text-xs">{t("kuzatuv.tavsiya_emas")}</p>
    </>
  );
}
