"use client";

import { useEffect, useState } from "react";

import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { bosqichKaliti } from "@/lib/oshxona";
import type { JonliHolat } from "@/lib/queries";

/** Jonli tahlil monitori — "oshxona ko'rinishi".
 *
 * Admin tizimning orqa fonda nima qilayotganini ko'zi bilan ko'radi:
 * har bir coin qaysi bosqichda, nima uchun to'xtadi.
 *
 * NIMA UCHUN POLLING, WebSocket EMAS: sikl har necha daqiqada bir
 * marta ishlaydi, ya'ni yangilanish tezligi baribir sikl tezligi bilan
 * cheklangan. WebSocket ulanishni ushlab turish va uzilishni qayta
 * tiklash muammosini qo'shardi, foyda esa bermasdi.
 *
 * OCHIQ AYTILADIGAN CHEKLOV: bu "sekin kino" emas. Sikl bir necha
 * soniyada barcha coinni ko'rib chiqadi, shuning uchun ekranda
 * OXIRGI SIKL natijasi turadi va har yangi siklda to'liq yangilanadi.
 * Foydasi shundan kamaymaydi: ikkala maqsad ham — "tizim ishlayaptimi"
 * va "qaysi bosqichda to'xtayapti" — shu ko'rinishdan javob oladi.
 */
export function JonliOshxona({
  boshlangich,
  matnlar,
  bosqichNomlari,
  interval = 5000,
}: {
  boshlangich: JonliHolat;
  matnlar: Record<string, string>;
  /** Bosqich KALITIDAN odam o'qiydigan nom — serverdan (tarjima bilan).
   *
   * Kalit bo'yicha, to'liq kod bo'yicha emas: pollingda ekranga
   * boshlang'ich holatda umuman bo'lmagan bosqichlar kelishi mumkin
   * (masalan boshqa strategiya). Kod bo'yicha yozilsa, ular xom
   * `opening_range_scalp:window` ko'rinishida chiqib qolardi. */
  bosqichNomlari: Record<string, string>;
  interval?: number;
}) {
  const [holat, setHolat] = useState(boshlangich);
  const [xato, setXato] = useState(false);

  useEffect(() => {
    let tirik = true;

    const yangila = async () => {
      try {
        const javob = await fetch("/api/jonli");
        if (!javob.ok) return;
        const yangi = (await javob.json()) as JonliHolat;
        if (!tirik) return;
        // `cycleAt` JSON dan matn bo'lib keladi — sanaga qaytaramiz
        setHolat({ ...yangi, cycleAt: yangi.cycleAt ? new Date(yangi.cycleAt) : null });
        setXato(false);
      } catch {
        // Tarmoq uzilsa oxirgi ma'lum holat qoladi — ekran bo'shab
        // qolmaydi. Lekin buni YASHIRMAYMIZ: eskirgan ma'lumotni
        // jonli deb ko'rsatish monitorning butun maqsadiga zid.
        if (tirik) setXato(true);
      }
    };

    const taymer = setInterval(yangila, interval);
    return () => {
      tirik = false;
      clearInterval(taymer);
    };
  }, [interval]);

  const nomi = (kod: string) => bosqichNomlari[bosqichKaliti(kod)] ?? kod;

  if (!holat.cycleAt) {
    return (
      <Card>
        <CardTitle>🔴 {matnlar.sarlavha}</CardTitle>
        <CardHint>{matnlar.yoq}</CardHint>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card variant="urgu">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <CardTitle>🔴 {matnlar.sarlavha}</CardTitle>
          <span className="text-matn-past raqam text-xs">
            {matnlar.oxirgi_sikl}: {holat.cycleAt.toISOString().slice(11, 19)} UTC
          </span>
        </div>
        <CardHint>{matnlar.izoh}</CardHint>

        {holat.xulosa && (
          <div className="border-ramka/40 mt-3 flex flex-wrap gap-x-5 gap-y-1 border-t pt-3 text-xs">
            <span>
              <span className="text-matn-past">{matnlar.jami}: </span>
              <span className="raqam text-sarlavha font-semibold">{holat.xulosa.jami}</span>
            </span>
            {holat.xulosa.signal > 0 && (
              <span className="text-yaxshi font-semibold">
                🎉 {holat.xulosa.signal} {matnlar.signal_soni}
              </span>
            )}
            {holat.xulosa.engKopBosqich && (
              <span>
                <span className="text-matn-past">{matnlar.eng_kop}: </span>
                <span className="text-sarlavha font-semibold">
                  {nomi(holat.xulosa.engKopBosqich)}
                </span>
                <span className="raqam text-matn-past"> ({holat.xulosa.engKopSoni})</span>
              </span>
            )}
            {holat.xulosa.ortachaBall !== null && (
              <span>
                <span className="text-matn-past">{matnlar.ortacha_ball}: </span>
                <span className="raqam text-sarlavha font-semibold">
                  {holat.xulosa.ortachaBall.toFixed(0)}
                </span>
                <span className="raqam text-matn-past">
                  {" "}
                  · {matnlar.eng_yuqori} {holat.xulosa.engYuqoriBall?.toFixed(0)}
                </span>
              </span>
            )}
          </div>
        )}

        <p className="text-matn-past mt-2 text-xs">{matnlar.kirish}</p>
        {xato && <p className="text-past mt-2 text-xs">⚠️ {matnlar.uzildi}</p>}
      </Card>

      {holat.siklToxtadi && (
        <Card>
          <p className="text-sm">
            <span aria-hidden>⛔ </span>
            <span className="text-past font-semibold">{matnlar.sikl_toxtadi}</span>
          </p>
          <p className="text-matn-past mt-1 text-sm">{holat.siklToxtadi}</p>
        </Card>
      )}

      {holat.coinlar.length === 0 && !holat.siklToxtadi && (
        <Card>
          <CardHint>{matnlar.coin_yoq}</CardHint>
        </Card>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {holat.coinlar.map((coin) => (
          <Card key={coin.symbol} variant={coin.signal ? "urgu" : undefined}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="text-sarlavha raqam font-bold">{coin.symbol}</span>
              {coin.signal ? (
                <span className="text-yaxshi text-xs font-semibold">
                  🎉 {matnlar.signal_chiqdi}
                </span>
              ) : (
                coin.score !== null && (
                  <span className="text-matn-past raqam text-xs">
                    {coin.score.toFixed(0)} {matnlar.ball}
                  </span>
                )
              )}
            </div>

            <ol className="mt-3 space-y-1.5">
              {coin.bosqichlar.map((b, i) => (
                <li key={`${b.stage}-${i}`} className="flex items-start gap-2 text-sm">
                  <span aria-hidden className="shrink-0">
                    {b.status === "pass" ? "✅" : b.status === "fail" ? "❌" : "⏳"}
                  </span>
                  <span
                    className={
                      b.status === "fail" ? "text-past" : "text-matn-past"
                    }
                  >
                    {nomi(b.stage)}
                    {b.reason && (
                      <span className="text-matn-past block text-xs">{b.reason}</span>
                    )}
                  </span>
                </li>
              ))}
            </ol>
          </Card>
        ))}
      </div>
    </div>
  );
}
