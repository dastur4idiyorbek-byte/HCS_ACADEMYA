import { cn } from "@/lib/cn";
import { BUTUN_KALITLAR, SOZLAMA_ORALIQLARI, type SozlamaKalit, shablon } from "@/lib/radar";

import type { Tarjimon } from "./matn";

export type SozlamaQatori = {
  kalit: SozlamaKalit;
  /** Hozir kuchdagi qiymat: admin qiymati, bo'lmasa YAML */
  joriy: number;
  /** YAML dagi standart */
  standart: number;
  /** Admin o'zgartirganmi */
  ozgartirilgan: boolean;
  /** Oxirgi sessiya aslida qaysi qiymat bilan hisoblangan */
  sessiyada: number | undefined;
};

/** Raqamni o'qiladigan qilib: 10000000 -> "10,000,000", 0.1 -> "0.1". */
function raqam(x: number): string {
  return x.toLocaleString("en-US", { maximumFractionDigits: 6 });
}

/** Admin sozlamalari (13-bo'lim): 18 ta chegara.
 *
 * O'zgarish KEYINGI sessiyadan ishlaydi — bot har sessiya boshida
 * `radar_sozlamalar` ni o'qiydi. Shu sababli har qator yonida
 * "oxirgi sessiyada: ..." ham ko'rsatiladi (agar farq qilsa): admin
 * qiymatni o'zgartirgan, lekin ekrandagi natija hali eski chegara
 * bilan hisoblangan bo'lishi mumkin.
 *
 * Brauzer tekshiruvi (`min`/`max`/`step`) faqat qulaylik: server
 * amali qiymatni `sozlamaTekshir` bilan QAYTA tekshiradi.
 */
export function Sozlamalar({
  qatorlar,
  saqla,
  tikla,
  t,
}: {
  qatorlar: SozlamaQatori[];
  saqla: (forma: FormData) => Promise<void>;
  tikla: (forma: FormData) => Promise<void>;
  t: Tarjimon;
}) {
  return (
    <ul className="divide-ramka-yumshoq/40 divide-y">
      {qatorlar.map((q) => {
        const [past, yuqori] = SOZLAMA_ORALIQLARI[q.kalit];
        const butun = BUTUN_KALITLAR.includes(q.kalit);
        const id = `sozlama-${q.kalit}`;
        return (
          <li key={q.kalit} className="py-3 first:pt-0 last:pb-0">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <label htmlFor={id} className="text-matn text-sm font-medium">
                {t(`radar.kalit.${q.kalit}`)}
              </label>
              {q.ozgartirilgan ? (
                <span className="text-ortacha text-[11px]">{t("radar.sozlama_ozgartirilgan")}</span>
              ) : null}
            </div>
            <p className="text-matn-past raqam mt-0.5 text-[11px]">
              {t("radar.sozlama_joriy")}:{" "}
              <span className={cn(q.ozgartirilgan ? "text-ortacha" : "text-matn")}>{raqam(q.joriy)}</span>
              {" · "}
              {t("radar.sozlama_standart")}: {raqam(q.standart)}
              {" · "}
              {t("radar.sozlama_oraliq")}: {raqam(past)} – {raqam(yuqori)}
              {butun ? ` (${t("radar.butun_son")})` : ""}
              {q.sessiyada !== undefined && q.sessiyada !== q.joriy
                ? ` · ${shablon(t("radar.sozlama_sessiyada"), { q: raqam(q.sessiyada) })}`
                : ""}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <form action={saqla} className="flex items-center gap-2">
                <input type="hidden" name="kalit" value={q.kalit} />
                <input
                  id={id}
                  name="qiymat"
                  type="number"
                  required
                  min={past}
                  max={yuqori}
                  step={butun ? 1 : "any"}
                  defaultValue={q.joriy}
                  className="border-ramka-yumshoq rounded-tugma bg-fon raqam w-40 border px-3 py-1.5 text-sm"
                />
                <button
                  type="submit"
                  className="bg-ramka rounded-tugma px-3 py-1.5 text-xs font-semibold text-[#0a2450] hover:brightness-110"
                >
                  {t("radar.saqlash")}
                </button>
              </form>
              {q.ozgartirilgan ? (
                <form action={tikla}>
                  <input type="hidden" name="kalit" value={q.kalit} />
                  <button
                    type="submit"
                    className="border-ramka-yumshoq text-matn-past hover:text-sarlavha rounded-tugma border px-3 py-1.5 text-xs"
                  >
                    {t("radar.standartga")}
                  </button>
                </form>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
