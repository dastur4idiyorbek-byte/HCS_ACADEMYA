"use client";

import { useState } from "react";

import { Kalkulyator } from "@/components/Kalkulyator";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";

/** Mustaqil kalkulyatorning tepasi: coin nomi va OCO izohi.
 *
 * NEGA ALOHIDA MIJOZ KOMPONENTI. Coin nomini foydalanuvchi yozadi va
 * u miqdorni qaysi aktivda ko'rsatishni belgilaydi (BTC uchun "BTC",
 * juftlik yozilsa asosiy aktiv ajratiladi). Ya'ni bu holat
 * brauzerda turishi kerak.
 *
 * Kalkulyatorning O'ZI qayta yozilmadi — signal sahifasidagi bilan
 * AYNAN bitta komponent. Ikkita nusxa bo'lsa, hisob vaqt o'tib
 * ikki xil bo'lib ketardi.
 */
export function KalkulyatorSahifa({
  kotirovka,
  matnlar,
}: {
  kotirovka: string;
  matnlar: Record<string, string>;
}) {
  const [symbol, setSymbol] = useState("BTC");

  return (
    <div className="space-y-5">
      <Card>
        <CardTitle className="flex items-center gap-2">
          <Ikonka nom="coinlar" />
          {matnlar.aktiv}
        </CardTitle>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="BTC"
          className="border-ramka-yumshoq rounded-tugma bg-fon raqam mt-3 w-full border px-3 py-2 text-sm uppercase sm:max-w-xs"
        />
      </Card>

      <Card>
        <CardTitle className="flex items-center gap-2">
          <Ikonka nom="tp" />
          {matnlar.oco_sarlavha}
        </CardTitle>
        {/* IZOH RO'YXATDAN OLDIN turadi: foydalanuvchi ulush
            maydonlarini ko'rishdan avval ular O'ZI moslashishini
            bilsin. Pastda tursa, "nega mening raqamim o'zgarib
            ketdi" degan savol tug'ilardi. */}
        <CardHint className="mt-2">{matnlar.oco_izoh}</CardHint>
      </Card>

      <Kalkulyator
        symbol={symbol || "BTC"}
        kotirovka={kotirovka}
        entry={0}
        stop={0}
        tpNarxlari={[0, 0]}
        tpBoshqaruvi
        matnlar={matnlar}
      />
    </div>
  );
}
