import {
  BLOK_NOMLARI,
  blokKorinishi,
  toliqZanjir,
  type BlokKorinishi,
  type CoinZanjiri,
} from "@/lib/zanjir";
import { Ikonka } from "@/components/ui/Ikonka";

/** Bitta coinning to'rt blokli zanjiri — animatsion (4-prompt, 3-qism).
 *
 * ANIMATSIYA NIMA QILADI VA NIMA QILMAYDI. Bloklar sahifa ochilganda
 * ketma-ket "yonib" chiqadi — chapdan o'ngga, zanjir hosil bo'layotgani
 * ko'rinadi. Bu — YOZILGAN holatning qayta o'ynatilishi, jonli oqim
 * EMAS: sikl har necha soatda yuradi va bir necha soniyada tugaydi,
 * ya'ni "hozir tekshirilmoqda" holatini ushlab turish deyarli imkonsiz.
 *
 * Buni yashirmaslik muhim: "jonli" ko'rinib, aslida eski raqam
 * ko'rsatadigan ekran — eng yomon turdagi interfeys.
 *
 * BUTUNLAY CSS. Hech qanday kutubxona yo'q, `animation-delay` bilan
 * navbat yasaladi. Harakatga sezgir foydalanuvchilar uchun
 * `prefers-reduced-motion` da animatsiya o'chadi (globals.css).
 */

const USLUB: Record<BlokKorinishi, string> = {
  // To'liq bog'langan — yorqin, to'q rangga "quyilgan"
  toliq: "border-yaxshi bg-yaxshi/15 text-yaxshi",
  // Qisman — yarim yorqin, zaifroq rang
  qisman: "border-ortacha bg-ortacha/10 text-ortacha",
  // Uzilgan — qizil, zanjir shu yerda to'xtaydi
  uzilgan: "border-past bg-past/10 text-past",
  // O'lchanmadi — zanjirni UZMAYDI, lekin kuch ham bermaydi
  olchanmadi: "border-ramka-yumshoq bg-panel text-matn-past border-dashed",
  // Umuman yurmagan — xira, bo'sh kontur
  tekshirilmagan: "border-ramka-yumshoq/50 bg-transparent text-matn-past/50",
};

/** Blok holati -> nuqta rangi.
 *
 * NEGA RANGLI NUQTA, EMOJI EMAS. Ilgari bu yerda 🟩🟨🟥 turardi va
 * ular tizim ranglari edi: bizning "yaxshi/o'rtacha/past" rangimizga
 * mos kelmasdi va yonidagi ramka bilan urishardi. Nuqta esa
 * `currentColor` ni oladi — katakning rangi qanday bo'lsa, nuqta
 * ham shunday.
 *
 * Rang YOLG'IZ ma'no tashimaydi: har katakda blok NOMI ham yozilgan
 * va ramka uslubi ham farq qiladi (uzilganda to'la, o'lchanmaganda
 * uzuq chiziq). Rang ko'rmaydigan odam ham o'qiy oladi. */
const NUQTA: Record<BlokKorinishi, string> = {
  toliq: "bg-current",
  qisman: "bg-current opacity-70",
  uzilgan: "bg-current",
  olchanmadi: "border border-current bg-transparent",
  tekshirilmagan: "bg-current opacity-40",
};

export function BlokZanjiri({ coin }: { coin: CoinZanjiri }) {
  const bloklar = toliqZanjir(coin);

  return (
    <div className="flex flex-wrap items-stretch gap-1.5">
      {bloklar.map((blok, i) => {
        const korinish = blokKorinishi(blok);
        const oldingiToliq = i > 0 && blokKorinishi(bloklar[i - 1]) === "toliq";

        return (
          <div key={BLOK_NOMLARI[i]} className="flex items-stretch gap-1.5">
            {i > 0 && (
              // Zanjir bo'g'ini: oldingi blok to'liq bo'lsa YONADI,
              // aks holda uzilgan bo'lib qoladi.
              <span
                aria-hidden
                className={
                  "zanjir-bogin self-center " +
                  (oldingiToliq
                    ? "zanjir-bogin--ulangan"
                    : "zanjir-bogin--uzilgan")
                }
                style={{ animationDelay: `${i * 160}ms` }}
              />
            )}
            <div
              className={
                "blok-katak rounded-tugma min-w-[5.5rem] border px-2.5 py-2 text-center " +
                USLUB[korinish]
              }
              style={{ animationDelay: `${i * 160}ms` }}
            >
              <div className="text-[10px] leading-tight uppercase opacity-80">
                {BLOK_NOMLARI[i]}
              </div>
              <div className="raqam mt-0.5 text-sm font-bold">
                {blok && !blok.olchanmadi ? `${blok.kuch}/${blok.maxraj}` : "—"}
              </div>
              <div className="mt-1 flex justify-center">
                <span
                  aria-hidden
                  className={`h-2 w-2 rounded-full ${NUQTA[korinish]}`}
                />
              </div>
            </div>
          </div>
        );
      })}

      {/* Signal chiqqan bo'lsa — zanjirning oxirida belgisi */}
      {coin.natija === "signal" && (
        <div
          className="blok-katak border-yaxshi bg-yaxshi/20 text-yaxshi rounded-tugma flex min-w-[5.5rem] items-center justify-center border px-2.5 py-2 text-sm font-bold"
          style={{ animationDelay: `${BLOK_NOMLARI.length * 160}ms` }}
        >
          <Ikonka nom="faol" className="mr-1.5 h-4 w-4" />
          SIGNAL
        </div>
      )}
    </div>
  );
}
