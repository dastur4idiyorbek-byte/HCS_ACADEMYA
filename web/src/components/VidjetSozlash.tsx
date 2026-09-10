"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";
import { VIDJETLAR, type VidjetKod } from "@/lib/vidjetlar";
import { Ikonka } from "@/components/ui/Ikonka";

/** Vidjetlarni tanlash va tartiblash.
 *
 * NEGA SURIB TASHLASH (drag & drop) EMAS. Surish sichqoncha bilan
 * qulay, telefonda esa qiyin: barmoq sahifani ham suradi va ikkisi
 * chalkashadi. Bizning foydalanuvchilarning ko'pi telefonda.
 * Yuqori/quyi tugmalari esa ikkala qurilmada bir xil ishlaydi va
 * klaviatura bilan ham yuriladi.
 *
 * TANLOV DARROV SAQLANMAYDI. "Saqlash" bosilgunicha o'zgarish faqat
 * ekranda turadi: odam bir necha narsani o'zgartirib, keyin fikridan
 * qaytishi mumkin. Har bosishda so'rov yuborilsa, "bekor qilish"
 * degan narsa bo'lmasdi.
 */
export function VidjetSozlash({
  boshlangich,
  yorliq,
  vidjetNomlari,
}: {
  boshlangich: VidjetKod[];
  yorliq: {
    sozlash: string;
    saqlash: string;
    bekor: string;
    tanlangan: string;
    mavjud: string;
    saqlandi: string;
    xato: string;
  };
  /** Vidjet kodi -> tarjima qilingan nomi. */
  vidjetNomlari: Record<string, string>;
}) {
  const [ochiq, setOchiq] = useState(false);
  const [tanlov, setTanlov] = useState<VidjetKod[]>(boshlangich);
  const [holat, setHolat] = useState<"tinch" | "yuborilmoqda" | "xato">(
    "tinch",
  );

  const tanlanmagan = VIDJETLAR.filter((v) => !tanlov.includes(v.kod));

  function kochir(indeks: number, yon: -1 | 1) {
    const yangi = [...tanlov];
    const nishon = indeks + yon;
    if (nishon < 0 || nishon >= yangi.length) return;
    [yangi[indeks], yangi[nishon]] = [yangi[nishon], yangi[indeks]];
    setTanlov(yangi);
  }

  async function saqla() {
    setHolat("yuborilmoqda");
    try {
      const javob = await fetch("/api/vidjet", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ vidjetlar: tanlov }),
      });
      if (!javob.ok) throw new Error();
      // Sahifa serverdan qayta yuklansin — vidjetlar server
      // komponentida chiziladi va yangi tartib faqat shundan keyin
      // ko'rinadi.
      window.location.reload();
    } catch {
      setHolat("xato");
    }
  }

  if (!ochiq) {
    return (
      <button
        type="button"
        onClick={() => setOchiq(true)}
        className="text-matn-past hover:text-sarlavha text-sm transition-colors"
      >
        <Ikonka nom="sozlamalar" className="h-4 w-4" />
        {yorliq.sozlash}
      </button>
    );
  }

  return (
    <div className="rounded-kartochka border-ramka-yumshoq mt-3 w-full border bg-white/[0.02] p-4">
      <p className="text-matn-past mb-2 text-[11px] tracking-wide uppercase">
        {yorliq.tanlangan}
      </p>
      <ul className="space-y-1.5">
        {tanlov.map((kod, i) => (
          <li
            key={kod}
            className="rounded-kichik flex items-center gap-2 border border-white/10 px-3 py-2 text-sm"
          >
            <span className="flex-1">{vidjetNomlari[kod] ?? kod}</span>
            <button
              type="button"
              onClick={() => kochir(i, -1)}
              disabled={i === 0}
              aria-label="Yuqoriga"
              className="text-matn-past hover:text-sarlavha px-1.5 disabled:opacity-30"
            >
              <Ikonka nom="tepaga" className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => kochir(i, 1)}
              disabled={i === tanlov.length - 1}
              aria-label="Quyiga"
              className="text-matn-past hover:text-sarlavha px-1.5 disabled:opacity-30"
            >
              <Ikonka nom="pastga" className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setTanlov(tanlov.filter((x) => x !== kod))}
              aria-label="Olib tashlash"
              className="text-matn-past hover:text-past px-1.5"
            >
              <Ikonka nom="yopish" className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>

      {tanlanmagan.length > 0 && (
        <>
          <p className="text-matn-past mt-4 mb-2 text-[11px] tracking-wide uppercase">
            {yorliq.mavjud}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {tanlanmagan.map((v) => (
              <button
                key={v.kod}
                type="button"
                onClick={() => setTanlov([...tanlov, v.kod])}
                className="rounded-kichik border-ramka-yumshoq hover:border-ramka border px-3 py-1.5 text-xs transition-colors"
              >
                + {vidjetNomlari[v.kod] ?? v.kod}
              </button>
            ))}
          </div>
        </>
      )}

      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={saqla}
          disabled={holat === "yuborilmoqda"}
          className={cn(
            "border-ramka rounded-tugma hover:bg-panel-yorqin border px-4 py-2 text-sm transition",
            holat === "yuborilmoqda" && "opacity-50",
          )}
        >
          {yorliq.saqlash}
        </button>
        <button
          type="button"
          onClick={() => {
            setTanlov(boshlangich);
            setOchiq(false);
            setHolat("tinch");
          }}
          className="text-matn-past hover:text-sarlavha text-sm transition-colors"
        >
          {yorliq.bekor}
        </button>
        {holat === "xato" && (
          <span className="text-past text-sm">{yorliq.xato}</span>
        )}
      </div>
    </div>
  );
}
