import { Card, CardTitle } from "@/components/ui/Card";

/** Vaqtinchalik holat — bo'lim yangi tahlil moduli bilan qaytadi.
 *
 * 2026-09-03 da eski tahlil moduli butunlay olib tashlandi
 * (docs/OCHIRISH_ROYXATI.md). Sahifalarning O'ZI qoldi: layout,
 * menyu bandi, manzil — hammasi joyida, faqat ma'lumot manbai
 * uzildi. Bo'sh jadval ko'rsatish o'rniga sabab yoziladi, aks
 * holda foydalanuvchi buni NOSOZLIK deb o'qirdi.
 */
export function Yangilanmoqda({
  sarlavha,
  izoh,
}: {
  sarlavha: string;
  izoh: string;
}) {
  return (
    <Card>
      <CardTitle>{sarlavha}</CardTitle>
      <div className="text-matn-past py-8 text-center text-sm">
        <div className="mb-2 text-3xl">🛠</div>
        <p>{izoh}</p>
      </div>
    </Card>
  );
}
