"use client";

import { useEffect, useRef, useState } from "react";
import { Ikonka } from "@/components/ui/Ikonka";

/** TradingView grafigi — rasmiy bepul embed widget.
 *
 * Nima uchun `useRef` va qo'lda qo'shish: widget `<script>` tegining
 * O'ZINI grafikka aylantiradi (u DOM ga yozadi), ya'ni uni React
 * boshqaradigan oddiy element sifatida qo'yib bo'lmaydi.
 *
 * Grafik SIGNAL HIMOYASIDAN TASHQARIDA turadi: bu ochiq bozor
 * ma'lumoti, bizning mahsulotimiz emas. Himoyalanadigan narsa — kirish,
 * Stop va TP narxlari.
 *
 * NEGA ZAXIRA HOLAT KERAK: bu widget uchinchi tomon skriptini tashqi
 * domendan tortadi. Reklama bloklovchi (uBlock va shunga o'xshash) uni
 * bemalol to'sadi, ayrim tarmoqlarda esa u umuman ochilmaydi. Zaxirasiz
 * foydalanuvchi 420px bo'sh quti ko'radi va sayt buzilgan deb o'ylaydi.
 * Shuning uchun: skript xato bersa yoki belgilangan vaqtda grafik
 * chizilmasa — tushuntirish matni chiqadi.
 */
export function Grafik({
  symbol,
  xatoMatni,
  dark = true,
}: {
  symbol: string;
  /** Grafik yuklanmasa ko'rsatiladigan matn */
  xatoMatni: string;
  dark?: boolean;
}) {
  const idish = useRef<HTMLDivElement>(null);
  const [xato, setXato] = useState(false);

  useEffect(() => {
    const joy = idish.current;
    if (!joy) return;

    setXato(false);

    const skript = document.createElement("script");
    skript.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    skript.async = true;
    skript.type = "text/javascript";
    skript.onerror = () => setXato(true);
    skript.innerHTML = JSON.stringify({
      symbol,
      interval: "240",
      timezone: "Etc/UTC",
      theme: dark ? "dark" : "light",
      style: "1",
      locale: "en",
      hide_side_toolbar: true,
      allow_symbol_change: false,
      save_image: false,
      autosize: true,
    });
    joy.appendChild(skript);

    // `onerror` hamma holatni tutmaydi: bloklovchi so'rovni jimgina
    // bekor qilsa yoki skript yuklanib, grafik chizilmasa ham xabar
    // kelmaydi. Shuning uchun natijani ham tekshiramiz — widget o'z
    // `iframe`ini qo'yganmi.
    const taymer = setTimeout(() => {
      if (!joy.querySelector("iframe")) setXato(true);
    }, 6000);

    return () => {
      clearTimeout(taymer);
      joy.replaceChildren();
    };
  }, [symbol, dark]);

  return (
    <div className="rounded-kartochka h-[320px] overflow-hidden sm:h-[420px]">
      <div
        ref={idish}
        className={`tradingview-widget-container h-full ${xato ? "hidden" : ""}`}
      >
        <div className="tradingview-widget-container__widget h-full" />
      </div>

      {xato && (
        <div className="flex h-full items-center justify-center p-4">
          <p className="text-matn-past max-w-md text-center text-sm leading-relaxed">
            <Ikonka nom="grafik" className="inline h-4 w-4 align-[-3px]" />{" "}
            {xatoMatni}
          </p>
        </div>
      )}
    </div>
  );
}
