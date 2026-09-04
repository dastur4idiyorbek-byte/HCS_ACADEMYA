"use client";

import { useState } from "react";

import { Grafik } from "@/components/Grafik";
import { Badge } from "@/components/ui/Badge";
import { foiz } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { TOIFALAR, tradingviewJuftligi } from "@/lib/terminallar";

/** Real narx terminallari — Bozor Salomatligi ostida (4-prompt, 2-qism).
 *
 * TAB tanlanadi -> o'sha toifadagi coinlar ro'yxati chiqadi -> coin
 * bosilsa TO'LIQ grafik ochiladi. Grafik mavjud `Grafik` komponenti
 * (TradingView), ya'ni yangi infratuzilma qurilmadi — faqat boshqa
 * kontekstda ishlatildi.
 *
 * NEGA MINI-GRAFIK EMAS, RO'YXAT: o'n ikkita alohida TradingView
 * widgeti bitta sahifada — o'n ikkita `iframe` va o'n ikkita tashqi
 * skript. Mobil qurilmada sahifa amalda ochilmasdi. Ro'yxat + bitta
 * to'liq grafik ham o'sha savolga javob beradi, lekin sahifani
 * o'ldirmaydi.
 *
 * FAQAT HALOL COINLAR: ro'yxat zanjir moduli kuzatadigan o'n ikki
 * coin bilan bir xil.
 */
export function Terminallar({
  til,
  ozgarishlar,
}: {
  til: "uz" | "ru";
  /** Coin -> 24 soatlik o'zgarish. Bo'sh bo'lsa foiz ko'rsatilmaydi. */
  ozgarishlar: Record<string, number>;
}) {
  const t = tarjimon(til);
  const [toifa, setToifa] = useState(TOIFALAR[0].kod);
  const [tanlangan, setTanlangan] = useState<string | null>(null);

  const joriy = TOIFALAR.find((x) => x.kod === toifa) ?? TOIFALAR[0];

  return (
    <div>
      <div
        role="tablist"
        aria-label={t("zanjir.terminallar")}
        className="flex flex-wrap gap-2"
      >
        {TOIFALAR.map((x) => (
          <button
            key={x.kod}
            role="tab"
            type="button"
            aria-selected={x.kod === toifa}
            onClick={() => {
              setToifa(x.kod);
              setTanlangan(null);
            }}
            className={
              "rounded-tugma border px-3 py-2 text-sm transition " +
              (x.kod === toifa
                ? "border-ramka bg-panel-yorqin text-sarlavha font-semibold"
                : "border-ramka-yumshoq hover:bg-panel-yorqin")
            }
          >
            {t(x.kalit)}
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-4">
        {joriy.guruhlar.map((guruh) => (
          <div key={guruh.nom}>
            <h3 className="text-matn-past mb-2 text-xs font-semibold tracking-wide uppercase">
              {guruh.nom}
            </h3>
            <div className="flex flex-wrap gap-2">
              {guruh.coinlar.map((coin) => {
                const pct = ozgarishlar[coin];
                const faol = tanlangan === coin;
                return (
                  <button
                    key={coin}
                    type="button"
                    onClick={() => setTanlangan(faol ? null : coin)}
                    aria-pressed={faol}
                    className={
                      "rounded-tugma flex items-center gap-2 border px-3 py-2 text-sm transition " +
                      (faol
                        ? "border-ramka bg-panel-yorqin text-sarlavha font-semibold"
                        : "border-ramka-yumshoq hover:bg-panel-yorqin")
                    }
                  >
                    <span className="raqam">{coin}</span>
                    {pct !== undefined && (
                      <Badge tone={pct >= 0 ? "yaxshi" : "past"}>
                        {foiz(pct, 1)}
                      </Badge>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {tanlangan && (
        <div className="mt-5">
          <p className="text-matn-past mb-2 text-sm">
            {tanlangan} — {t("zanjir.terminallar")}
          </p>
          <Grafik
            symbol={tradingviewJuftligi(tanlangan)}
            xatoMatni={t("signal.grafik_xato")}
          />
        </div>
      )}
    </div>
  );
}
