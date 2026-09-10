"use client";

import { useMemo, useState } from "react";

import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import {
  ULUSH_JAMI,
  asosiyAktiv,
  hisobla,
  musbatSon,
  narxMatni,
  tengUlushlar,
  ulushlarniTengla,
} from "@/lib/kalkulyator";

/** Trading kalkulyatori — brauzerda, real vaqtda.
 *
 * Backend so'rovi YO'Q: foydalanuvchi summani yoki ulushni o'zgartirsa,
 * natija darhol qayta hisoblanadi. Hisob-kitobning o'zi
 * `lib/kalkulyator.ts` da — u sof funksiya va test bilan qoplangan.
 *
 * TP soni signaldan keladi. Hozircha signalda ikkita TP bor, lekin
 * komponent massiv qabul qiladi: uchinchisi qo'shilsa, bu yerda hech
 * narsa o'zgarmaydi.
 */

type Matnli = { narx: string; ulush: string };

const uslub =
  "border-ramka-yumshoq rounded-tugma bg-fon raqam w-full border px-3 py-2 text-sm";

export function Kalkulyator({
  symbol,
  kotirovka = "USDT",
  entry,
  stop,
  tpNarxlari,
  olinganTplar,
  boshlangichSumma,
  matnlar,
}: {
  symbol: string;
  /** Spot juftlik kotirovkasi — miqdorni to'g'ri aktivda ko'rsatish uchun */
  kotirovka?: string;
  entry: number;
  stop: number;
  tpNarxlari: number[];
  /** Qaysi TP lar ALLAQACHON olingan (signal holatidan).
   *
   *  Olingan TP o'chirilmaydi — u FAKT: pul qo'lda. O'chirilsa,
   *  kalkulyator olingan foydani yo'qotib, "hech narsa yo'q" degan
   *  yolg'on manzara ko'rsatardi. O'rniga u qulflanadi va alohida
   *  sanaladi. */
  olinganTplar?: boolean[];
  /** Boshlang'ich summa — TIZIM TAKLIFI (balans va Stop masofasidan).
   *  Berilmasa 1000 qo'yiladi: bu faqat balans kiritilmagan holat. */
  boshlangichSumma?: number | null;
  matnlar: Record<string, string>;
}) {
  const aktiv = asosiyAktiv(symbol, kotirovka);
  // Avval bu yerda QATTIQ "1000" turardi va u hech kimning haqiqiy
  // holatiga mos kelmasdi. Endi tizim taklifi tushadi — ya'ni
  // kalkulyator kartochkadagi "Miqdor" bilan bir xil raqamdan
  // boshlanadi va foydalanuvchi ikki xil son ko'rmaydi.
  const [summa, setSumma] = useState(() =>
    boshlangichSumma && boshlangichSumma > 0
      ? boshlangichSumma.toFixed(2)
      : "1000",
  );
  // `String(entry)` EMAS: bazadagi son `0.8294354680460917` boʻlib
  // chiqishi mumkin va maydonda shundayligicha turardi — uni oʻqib ham,
  // tahrirlab ham boʻlmaydi.
  const [kirish, setKirish] = useState(() => narxMatni(entry));
  const [stopMatn, setStopMatn] = useState(() => narxMatni(stop));
  const [tplar, setTplar] = useState<Matnli[]>(() => {
    const ulushlar = tengUlushlar(tpNarxlari.length);
    return tpNarxlari.map((n, i) => ({
      narx: narxMatni(n),
      ulush: String(ulushlar[i]),
    }));
  });

  const olindi = (i: number) => Boolean(olinganTplar?.[i]);
  // Bittasi ham olingan bo'lsa, ulushlar TARIXIY FAKT bo'lib qoladi:
  // o'sha ulushda sotilgan. Ularni tahrirlash "boshqacha sotgan
  // bo'lsam" degan xayoliy hisob bo'lardi.
  const qulflangan = Boolean(olinganTplar?.some(Boolean));

  const hisob = useMemo(() => {
    const s = musbatSon(summa);
    const e = musbatSon(kirish);
    if (s === null || e === null) return null;
    return hisobla(
      s,
      e,
      musbatSon(stopMatn) ?? 0,
      tplar.map((t, i) => ({
        narx: musbatSon(t.narx) ?? 0,
        ulush: Number(t.ulush.replace(",", ".")) || 0,
        olindi: Boolean(olinganTplar?.[i]),
      })),
    );
  }, [summa, kirish, stopMatn, tplar, olinganTplar]);

  const narxYangila = (i: number, qiymat: string) =>
    setTplar((oldingi) =>
      oldingi.map((t, j) => (i === j ? { ...t, narx: qiymat } : t)),
    );

  /** Ulush o'zgarsa QOLGANLARI qayta hisoblanadi.
   *
   * Tahrirlanayotgan maydonda foydalanuvchi YOZGAN matn qoladi (u hali
   * "7." kabi tugallanmagan bo'lishi mumkin), boshqalari esa sondan
   * qayta yasaladi. Shu sababdan yig'indi doim 100 bo'ladi va
   * "ulushlar 125%" holati umuman yuzaga kelmaydi. */
  const ulushYangila = (i: number, qiymat: string) =>
    setTplar((oldingi) => {
      const sonlar = oldingi.map((t) => Number(t.ulush.replace(",", ".")) || 0);
      const yangilari = ulushlarniTengla(
        sonlar,
        i,
        Number(qiymat.replace(",", ".")) || 0,
      );
      return oldingi.map((t, j) => ({
        narx: t.narx,
        ulush: j === i ? qiymat : String(yangilari[j]),
      }));
    });

  // Nol uchun belgi qo'yilmaydi: breakeven Stopda "+$0.00" degan yozuv
  // "biroz foyda" degan taassurot berardi, aslida esa hech narsa yo'q.
  const pul = (x: number) => {
    const belgi = Math.abs(x) < 0.005 ? "" : x > 0 ? "+" : "−";
    return `${belgi}$${Math.abs(x).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };
  const foiz = (x: number) => `${x >= 0 ? "+" : ""}${x.toFixed(2)}%`;
  const miqdor = (x: number) =>
    x.toLocaleString("en-US", { maximumFractionDigits: 8 });

  return (
    <Card>
      <CardTitle className="flex items-center gap-2">
        <Ikonka nom="kalkulyator" />
        {matnlar.sarlavha}
      </CardTitle>

      <div className="mt-4 space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="text-matn-past mb-1 block text-xs uppercase">
              {matnlar.summa}
            </span>
            <input
              inputMode="decimal"
              value={summa}
              onChange={(e) => setSumma(e.target.value)}
              className={uslub}
            />
          </label>
          <label className="block">
            <span className="text-matn-past mb-1 block text-xs uppercase">
              {matnlar.kalk_kirish}
            </span>
            {/* Kirish narxi TP olingandan keyin TAHRIRLANMAYDI: u
                allaqachon amalga oshgan savdoning narxi. Tahrirlansa,
                olingan foyda ham "qayta hisoblanib" ketardi. */}
            <input
              inputMode="decimal"
              value={kirish}
              onChange={(e) => setKirish(e.target.value)}
              disabled={qulflangan}
              className={`${uslub}${qulflangan ? " opacity-60" : ""}`}
            />
          </label>
          <label className="block">
            <span className="text-matn-past mb-1 block text-xs uppercase">
              {matnlar.kalk_stop}
            </span>
            <input
              inputMode="decimal"
              value={stopMatn}
              onChange={(e) => setStopMatn(e.target.value)}
              className={uslub}
            />
          </label>
        </div>

        {tplar.map((t, i) => (
          <div key={i} className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-matn-past mb-1 block text-xs uppercase">
                {`TP${i + 1}`}
              </span>
              <input
                inputMode="decimal"
                value={t.narx}
                onChange={(e) => narxYangila(i, e.target.value)}
                disabled={olindi(i)}
                className={`${uslub}${olindi(i) ? " opacity-60" : ""}`}
              />
            </label>
            <label className="block">
              <span className="text-matn-past mb-1 block text-xs uppercase">
                {matnlar.ulush} %
              </span>
              <input
                inputMode="decimal"
                value={t.ulush}
                onChange={(e) => ulushYangila(i, e.target.value)}
                disabled={qulflangan}
                className={`${uslub}${qulflangan ? " opacity-60" : ""}`}
              />
            </label>
          </div>
        ))}
      </div>

      {hisob && (
        <div className="border-ramka-yumshoq rounded-kichik mt-4 border p-3">
          <p className="text-matn-past raqam text-xs">
            {matnlar.umumiy}: {miqdor(hisob.umumiyMiqdor)} {aktiv}
            {hisob.sotilganMiqdor > 0 && (
              <>
                {" · "}
                {matnlar.kalk_qolgan}: {miqdor(hisob.qolganMiqdor)} {aktiv}
              </>
            )}
          </p>

          <ul className="mt-3 space-y-2">
            {hisob.tplar.map((t, i) => (
              <li
                key={i}
                className="flex flex-wrap items-baseline justify-between gap-2 text-sm"
              >
                <span>
                  <Ikonka
                    nom={t.olindi ? "faol" : "tp"}
                    className="inline h-4 w-4 align-[-3px]"
                  />{" "}
                  TP{i + 1}
                  {t.olindi && (
                    <span className="text-yaxshi text-xs">
                      {" "}
                      {matnlar.kalk_olindi}
                    </span>
                  )}{" "}
                  <span className="text-matn-past raqam text-xs">
                    ({t.ulush}% — {miqdor(t.miqdor)} {aktiv})
                  </span>
                </span>
                <span className="raqam text-yaxshi font-semibold">
                  {pul(t.foyda)}{" "}
                  <span className="text-matn-past text-xs">
                    ({foiz(t.foizOzgarish)})
                  </span>
                </span>
              </li>
            ))}

            <li className="flex flex-wrap items-baseline justify-between gap-2 border-t border-white/10 pt-2 text-sm">
              <span>
                <Ikonka nom="stop" className="inline h-4 w-4 align-[-3px]" />{" "}
                {matnlar.stop_agar}{" "}
                <span className="text-matn-past text-xs">
                  (
                  {((hisob.qolganMiqdor / hisob.umumiyMiqdor) * 100).toFixed(0)}
                  %
                  {hisob.sotilganMiqdor > 0
                    ? ` — ${matnlar.kalk_qolganiga}`
                    : ""}
                  )
                </span>
              </span>
              <span className="raqam text-past font-semibold">
                {pul(-hisob.stopZarar)}{" "}
                <span className="text-matn-past text-xs">
                  ({foiz(hisob.stopFoiz)})
                </span>
              </span>
            </li>
          </ul>

          {/* ENG MUHIM QATOR — TP olingandan keyin. "Stop bo'lsa nima
              bo'ladi?" degan savolga javob endi sof zarar emas: olingan
              foyda uni qoplaydi yoki hatto ortadi. */}
          {hisob.olinganFoyda > 0 && (
            <div className="border-ramka/50 mt-3 space-y-1 border-t pt-3 text-sm">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-matn-past">{matnlar.kalk_qolda}</span>
                <span className="raqam text-yaxshi font-semibold">
                  {pul(hisob.olinganFoyda)}
                </span>
              </div>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-matn-past">
                  <Ikonka nom="tp" className="inline h-4 w-4 align-[-3px]" />{" "}
                  {matnlar.kalk_kutilmoqda}
                </span>
                <span className="raqam font-semibold">
                  {pul(hisob.kutilayotganFoyda)}
                </span>
              </div>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-matn-past">
                  <Ikonka
                    nom="himoya"
                    className="inline h-4 w-4 align-[-3px]"
                  />{" "}
                  {matnlar.kalk_eng_yomon}
                </span>
                <span
                  className={`raqam font-semibold ${
                    hisob.engYomon >= 0 ? "text-yaxshi" : "text-past"
                  }`}
                >
                  {pul(hisob.engYomon)}
                </span>
              </div>
            </div>
          )}

          <div className="border-ramka/50 mt-3 flex flex-wrap items-baseline justify-between gap-2 border-t pt-3">
            <span className="text-sm font-semibold">
              <Ikonka nom="pul" className="inline h-4 w-4 align-[-3px]" />{" "}
              {matnlar.jami}
            </span>
            <span className="raqam text-sarlavha text-lg font-bold">
              {pul(hisob.jamiFoyda)}{" "}
              <span className="text-matn-past text-sm">
                ({foiz(hisob.jamiFoiz)})
              </span>
            </span>
          </div>
        </div>
      )}

      <CardHint className="mt-3">ℹ️ {matnlar.ogohlantirish}</CardHint>
    </Card>
  );
}

export { ULUSH_JAMI };
