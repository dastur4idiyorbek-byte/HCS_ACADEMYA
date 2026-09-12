import { cn } from "@/lib/cn";
import type { Segment } from "@/lib/kuzatuv";

/** Diqqat darajasi — SEGMENTLI, chapdan o'ngga to'ladigan indikator.
 *
 * 5.2-QISM TALABI: bu VIZUAL element, "3/4" degan matn EMAS. Matn
 * qo'shimcha bo'lib, indikator YONIDA, kichikroq shriftda turadi.
 *
 * UCHINCHI HOLAT KERAK. Segment ✅ va ❌ dan tashqari ⚪ ham
 * bo'lishi mumkin — o'lchanmagan. Uni "yo'q" deb chizish yolg'on
 * bo'lardi: biz salbiy javob olmadik, biz umuman o'lchamadik.
 * Farqi ko'rinadi: ❌ — to'q qizil kontur, ⚪ — deyarli ko'rinmas.
 *
 * SVG EMAS, CSS. Segment — oddiy to'rtburchak; SVG unga hech narsa
 * qo'shmaydi, lekin har coin qatorida bittadan SVG chizish uzun
 * ro'yxatda sezilarli yuk bo'lardi.
 */
export function Segmentlar({
  segmentlar,
  kichik = false,
  className,
}: {
  segmentlar: Segment[];
  /** "+10" ro'yxati uchun — ikkinchi darajali ko'rinish */
  kichik?: boolean;
  className?: string;
}) {
  const yoqilgan = segmentlar.filter((s) => s.holat === "ha").length;
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="flex items-center gap-1"
        role="img"
        aria-label={`Diqqat darajasi: ${yoqilgan} / ${segmentlar.length}`}
      >
        {segmentlar.map((s, i) => (
          <span
            key={`${s.nom}-${i}`}
            title={`${s.nom}: ${s.izoh}`}
            className={cn(
              "rounded-[3px] border",
              kichik ? "h-3 w-3.5" : "h-4 w-5",
              s.holat === "ha"
                ? "border-yaxshi bg-yaxshi"
                : s.holat === "yoq"
                  ? "border-past/60 bg-transparent"
                  : "border-ramka-yumshoq bg-transparent opacity-40",
            )}
          />
        ))}
      </div>
      <span
        className={cn(
          "tabular-nums",
          kichik ? "text-[11px]" : "text-xs",
          yoqilgan > 0 ? "text-matn" : "text-matn-past",
        )}
      >
        {yoqilgan}/{segmentlar.length}
      </span>
    </div>
  );
}
