import { Sarlavha } from "@/components/ui/Sarlavha";
import { Yangilanmoqda } from "@/components/Yangilanmoqda";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** BOZOR KO'RINISHI — VAQTINCHALIK to'xtatilgan.
 *
 * Postni bot qurardi (`bot/services/bozor_korinishi.py`), u esa
 * `core/analysis/bozor_korinishi.py` ga tayanardi. Ikkalasi ham
 * 2026-09-03 da olib tashlandi, ya'ni yangi post yozilmaydi.
 * Sahifa qoldi: manzil va menyu bandi buzilmasin.
 */
export default async function Bozor() {
  const { til } = await kirim();
  const t = tarjimon(til);

  return (
    <div className="space-y-4">
      <Sarlavha matn={t("menyu.bozor")} />
      <Yangilanmoqda sarlavha={t("menyu.bozor")} izoh={t("umumiy.yangilanmoqda")} />
    </div>
  );
}
