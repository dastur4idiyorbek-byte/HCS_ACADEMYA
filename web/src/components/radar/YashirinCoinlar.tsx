import { Badge } from "@/components/ui/Badge";
import type { YashirinCoin } from "@/lib/radar-baza";
import { YASHIRISH_MUDDATLARI, shablon } from "@/lib/radar";

import { type Tarjimon, vaqtMatni } from "./matn";

/** Yashirin coinlar (13-bo'lim): qo'shish formasi va ro'yxat.
 *
 * Yashirilgan coin O'RIN OLMAYDI, lekin bot uni baribir tekshiradi va
 * calibration'ga yozadi — aks holda "shovqinli" coinlarni yashirish
 * statistikani buzardi. Sahifa buni ochiq yozadi.
 *
 * Muddati o'tgan yozuv ham ko'rinadi (belgi bilan): bot uni hisobga
 * olmaydi, lekin admin ro'yxatni tozalashi mumkin.
 */
export function YashirinCoinlar({
  royxat,
  hozir,
  zona,
  yashir,
  och,
  t,
}: {
  royxat: YashirinCoin[];
  hozir: Date;
  zona: string;
  yashir: (forma: FormData) => Promise<void>;
  och: (forma: FormData) => Promise<void>;
  t: Tarjimon;
}) {
  return (
    <div className="space-y-4">
      <form action={yashir} className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-matn-past">{t("radar.symbol")}</span>
          <input
            name="symbol"
            required
            maxLength={34}
            autoComplete="off"
            placeholder="LSKUSDT"
            className="border-ramka-yumshoq rounded-tugma bg-fon w-40 border px-3 py-1.5 text-sm uppercase"
          />
        </label>
        <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs">
          <span className="text-matn-past">{t("radar.sabab_maydon")}</span>
          <input
            name="sabab"
            maxLength={300}
            className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-1.5 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-matn-past">{t("radar.muddat_maydon")}</span>
          <select
            name="muddat"
            defaultValue="7"
            className="border-ramka-yumshoq rounded-tugma bg-fon border px-3 py-1.5 text-sm"
          >
            {YASHIRISH_MUDDATLARI.map((m) => (
              <option key={m} value={m}>
                {t(`radar.muddat.${m}`)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="bg-ramka rounded-tugma px-4 py-2 text-xs font-semibold text-[#0a2450] hover:brightness-110"
        >
          {t("radar.yashir")}
        </button>
      </form>

      {royxat.length === 0 ? (
        <p className="text-matn-past text-sm">{t("radar.yashirin_bosh")}</p>
      ) : (
        <ul className="space-y-2">
          {royxat.map((y) => {
            const tugagan = y.gacha !== null && y.gacha.getTime() <= hozir.getTime();
            return (
              <li
                key={y.symbol}
                className="border-ramka-yumshoq rounded-kichik flex flex-wrap items-start justify-between gap-2 border p-3"
              >
                <span className="min-w-0">
                  <span className="text-sarlavha flex items-center gap-2 text-sm font-semibold">
                    {y.symbol}
                    {tugagan ? <Badge tone="neytral">{t("radar.muddati_tugagan")}</Badge> : null}
                  </span>
                  {y.sabab ? (
                    <span className="text-matn-past block text-xs break-words">{y.sabab}</span>
                  ) : null}
                  <span className="text-matn-past raqam block text-[11px]">
                    {y.gacha
                      ? shablon(t("radar.gacha"), { v: vaqtMatni(t, y.gacha, zona) })
                      : t("radar.doimiy")}
                  </span>
                </span>
                <form action={och}>
                  <input type="hidden" name="symbol" value={y.symbol} />
                  <button
                    type="submit"
                    className="border-ramka-yumshoq text-sarlavha hover:bg-panel-yorqin rounded-tugma border px-2.5 py-1 text-xs"
                  >
                    {t("radar.ochish")}
                  </button>
                </form>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
