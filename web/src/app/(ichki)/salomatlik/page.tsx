import { Sarlavha } from "@/components/ui/Sarlavha";
import { Yangilanmoqda } from "@/components/Yangilanmoqda";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Bozor Salomatligi va "nega signal yo'q" — VAQTINCHALIK to'xtatilgan.
 *
 * Sahifa o'chirilmadi: manzil, menyu bandi va layout joyida qoladi.
 * Ichidagi ikkita manba — eski indeks formulasi va eski voronka
 * bosqichlari — 2026-09-03 da tahlil moduli bilan birga olib
 * tashlandi. Eski yozuvlarni ko'rsatish yolg'on bo'lardi: ular
 * endi yangilanmaydi.
 */
export default async function Salomatlik() {
  const { til } = await kirim();
  const t = tarjimon(til);

  return (
    <div className="space-y-4">
      <Sarlavha matn={t("salomatlik.sarlavha")} />
      <Yangilanmoqda
        sarlavha={t("salomatlik.sarlavha")}
        izoh={t("umumiy.yangilanmoqda")}
      />
    </div>
  );
}
