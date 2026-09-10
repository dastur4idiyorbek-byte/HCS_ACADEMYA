import { KalkulyatorSahifa } from "@/components/KalkulyatorSahifa";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { kotirovka } from "@/lib/config";
import { kalkulyatorMatnlari, tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

/** MUSTAQIL TRADING KALKULYATORI.
 *
 * NEGA ALOHIDA SAHIFA. Kalkulyator shu paytgacha faqat signal
 * sahifasi ichida turardi va raqamlarni SIGNALDAN olardi. Avtomatik
 * signal 2026-09-10 da to'xtatilgach, foydalanuvchida o'z savdosini
 * hisoblaydigan joy qolmadi.
 *
 * BU YERDA TIZIM HECH NARSA TAVSIYA QILMAYDI. Summani ham, kirish va
 * Stop narxini ham, nishonlarni ham foydalanuvchining o'zi yozadi.
 * Xavf moduli (`core/risk_engine`) bu sahifaga UMUMAN tegmaydi —
 * "tizim shuncha oling dedi" degan taassurot bo'lmasligi kerak.
 *
 * BAZAGA HECH NARSA YOZILMAYDI: hisob brauzerda, sof funksiya bilan
 * (`lib/kalkulyator.ts`). Server so'rovi ham yo'q.
 */
export default async function Kalkulyator() {
  const { til } = await kirim();
  const t = tarjimon(til);

  return (
    <>
      <Sarlavha
        matn={t("kalk.sarlavha")}
        izoh={t("kalk.izoh")}
        belgi="kalkulyator"
      />
      <KalkulyatorSahifa
        kotirovka={kotirovka()}
        matnlar={{
          ...kalkulyatorMatnlari(t),
          // Kartochka sarlavhasi sahifa sarlavhasini TAKRORLAMASIN:
          // signal sahifasida "Trading kalkulyatori" o'rinli, bu yerda
          // esa u sahifa nomining o'zi va ikki marta yozilardi.
          sarlavha: t("kalk.hisob"),
          aktiv: t("kalk.aktiv"),
          oco_sarlavha: t("kalk.oco_sarlavha"),
          oco_izoh: t("kalk.oco_izoh"),
        }}
      />
    </>
  );
}
