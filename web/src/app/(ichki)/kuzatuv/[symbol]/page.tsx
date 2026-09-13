import Link from "next/link";
import { notFound } from "next/navigation";

import { BozorKesimi, pul } from "@/components/kuzatuv/BozorKesimi";
import { JonliStakan } from "@/components/kuzatuv/JonliStakan";
import { Segmentlar } from "@/components/kuzatuv/Segmentlar";
import { Card } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { cn } from "@/lib/cn";
import { tarjimon } from "@/lib/i18n";
import { BLOK_KALITI, SEGMENT_KALITI, blokRangi, type KuzatuvBlok } from "@/lib/kuzatuv";
import type { IkonkaNomi } from "@/components/ui/Ikonka";
import { kuzatuvBozori, kuzatuvCoin } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Bitta coinning chuqur ko'rinishi — FAQAT ADMIN (5.3-qism).
 *
 * Har blok ALOHIDA KARTA, rangli ramka bilan:
 *   yashil  — blok o'tdi
 *   kulrang — o'tmadi
 *   xira    — o'lchanmadi (manba yo'q). Bu UCHINCHI holat:
 *             "yo'q" emas, "bilmaymiz".
 *
 * Har tekshiruv yonida QAYSI GRAFIKDAN o'qilgani yoziladi. Raqam
 * qo'lda yozilmagan — u Pythondan keladi, config o'zgarsa yozuv
 * ham o'zgaradi.
 *
 * QAT'IY CHEGARA: Entry, Stop, TP YO'Q. Zona narxi ko'rsatiladi,
 * lekin u kirish narxi EMAS — sahifa buni ochiq aytadi.
 */
export default async function CoinSahifasi({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = await params;
  const { admin, til } = await kirim();
  const t = tarjimon(til);

  if (!admin) {
    return (
      <>
        <Sarlavha matn={t("kuzatuv.sarlavha")} belgi="korish" />
        <Card>
          <p className="text-past text-sm">{t("admin.faqat_admin")}</p>
        </Card>
      </>
    );
  }

  const coin = kuzatuvCoin(symbol);
  if (!coin) notFound();

  // Jonli ma'lumot FAQAT Top 20 uchun yig'iladi (6-qism).
  // Coin "+10" da yoki ro'yxatdan tashqarida bo'lsa — `null`,
  // va sahifa buni ochiq aytadi.
  const bozor = coin.royxat === "top" ? kuzatuvBozori(coin.symbol) : null;

  // Zona qaysi grafikdan — segmentdan OLINADI, qo'lda yozilmaydi.
  const timeframeZona =
    coin.segmentlar.find((s) => s.nom === "zona_konfluensiya")?.timeframe ?? "";

  return (
    <>
      <Link
        href="/kuzatuv"
        className="text-matn-past hover:text-sarlavha mb-3 inline-flex items-center gap-1.5 text-sm"
      >
        <Ikonka nom="qosh" className="h-4 w-4 rotate-180" />
        {t("kuzatuv.qaytish")}
      </Link>

      <Sarlavha matn={`${coin.symbol}/USDT`} belgi="korish" />

      {coin.ogohlantirish ? (
        <Card variant="urgu" className="border-ortacha mb-4">
          <p className="text-ortacha flex items-start gap-2 text-sm">
            <Ikonka nom="ogohlantirish" className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              <strong>{t("kuzatuv.ogohlantirish")}:</strong> {coin.ogohlantirish}
            </span>
          </p>
        </Card>
      ) : null}

      <Card className="mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-matn-past mb-1 text-xs">{t("kuzatuv.diqqat")}</p>
            <Segmentlar segmentlar={coin.segmentlar} />
          </div>
          <div className="text-right text-sm">
            <p className="text-sarlavha font-semibold">
              {t(`kuzatuv.yonalish.${coin.yonalish}`)}
            </p>
            <p className="text-matn-past text-xs">{coin.yonalishIzoh}</p>
          </div>
        </div>

        {/* IKKINCHI DARVOZA — narx harakatning qayerida.
            Struktura to'g'ri bo'lsa ham, harakat allaqachon
            bo'lgan coin ro'yxatga kirmaydi. */}
        <div className="border-ramka-yumshoq mt-3 border-t pt-3">
          <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-2">
            <span className="text-matn-past text-xs">{t("kuzatuv.bosqich")}</span>
            <span
              className={cn(
                "text-sm font-medium",
                coin.bosqich === "yurgan"
                  ? "text-past"
                  : coin.bosqich === "korreksiya"
                    ? "text-yaxshi"
                    : "text-matn",
              )}
            >
              {t(`kuzatuv.bosqich_holat.${coin.bosqich}`)}
            </span>
          </div>

          {coin.bosqichUlush !== null &&
          coin.impulsPast !== null &&
          coin.impulsYuqori !== null ? (
            <>
              <div className="text-matn-past mb-1 flex justify-between text-[11px] tabular-nums">
                <span>{coin.impulsPast.toPrecision(5)}</span>
                <span>{t("kuzatuv.impuls_orin")}: {coin.bosqichUlush}%</span>
                <span>{coin.impulsYuqori.toPrecision(5)}</span>
              </div>
              <div className="bg-panel-yorqin relative h-1.5 overflow-hidden rounded-full">
                {/* Qaytish zonasi — 38.2%..61.8% */}
                <div
                  aria-hidden
                  className="bg-yaxshi/25 absolute inset-y-0"
                  style={{ left: "38.2%", right: "38.2%" }}
                />
                <div
                  className={cn(
                    "absolute top-0 h-full w-1 rounded-full",
                    coin.bosqich === "yurgan" ? "bg-past" : "bg-sarlavha",
                  )}
                  style={{
                    left: `calc(${Math.min(100, Math.max(0, coin.bosqichUlush))}% - 2px)`,
                  }}
                />
              </div>
            </>
          ) : null}
          <p className="text-matn-past mt-1.5 text-xs">{coin.bosqichIzoh}</p>
        </div>
      </Card>

      <div className="mb-4 space-y-2">
        {coin.segmentlar.map((s, i) => (
          <div
            key={`${s.nom}-${i}`}
            className="rounded-kartochka border-ramka-yumshoq bg-panel flex items-start gap-3 border p-3"
          >
            <span
              className={cn(
                "mt-0.5 h-3.5 w-3.5 shrink-0 rounded-[3px] border",
                s.holat === "ha"
                  ? "border-yaxshi bg-yaxshi"
                  : s.holat === "yoq"
                    ? "border-past/60"
                    : "border-ramka-yumshoq opacity-40",
              )}
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {SEGMENT_KALITI[s.nom] ? t(SEGMENT_KALITI[s.nom]) : s.nom}
              </p>
              <p className="text-matn-past text-xs">{s.izoh}</p>
            </div>
            <span className="text-matn-past shrink-0 text-[11px]">
              {t("kuzatuv.grafik")}: {s.timeframe}
            </span>
          </div>
        ))}
      </div>

      {/* ANIQ NARX DARAJALARI — 5.3-qism uch marta so'raydi.
          Blok tekshiruvlarining izohida bu raqamlar yo'q: ular
          faqat "bor/yo'q" deydi. Shuning uchun alohida bo'lim. */}
      {coin.zonaPast !== null || coin.bosNarx !== null || coin.sweepNarx !== null ? (
        <Card className="mb-4">
          <p className="text-matn-past mb-2 flex items-center gap-1.5 text-xs">
            <Ikonka nom="narx" className="h-3.5 w-3.5" />
            {t("kuzatuv.darajalar")}
          </p>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <Raqam
              nom={`${t("kuzatuv.support")} · ${coin.zonaPast !== null ? timeframeZona : ""}`}
              qiymat={daraja(coin.zonaPast)}
            />
            <Raqam nom={t("kuzatuv.resistance")} qiymat={daraja(coin.zonaYuqori)} />
            <Raqam nom={t("kuzatuv.bos_daraja")} qiymat={daraja(coin.bosNarx)} />
            <Raqam nom={t("kuzatuv.sweep_daraja")} qiymat={daraja(coin.sweepNarx)} />
          </div>
        </Card>
      ) : null}

      <div className="mb-5 grid gap-3 sm:grid-cols-2">
        {coin.bloklar.map((b) => (
          <BlokKartasi key={b.nom} blok={b} t={t} />
        ))}
      </div>

      <h2 className="text-sarlavha mb-2 text-sm font-semibold">
        {t("kuzatuv.bozor")}
      </h2>

      {coin.royxat === "top" ? (
        <>
          {bozor ? (
            <>
              {/* CoinGecko kesimi — admin uchun TO'LIQ */}
              <BozorKesimi bozor={bozor} t={t} toliq />

              {/* Bizning o'z yig'mamiz — 15 daqiqalik oyna */}
              <Card className="mb-3">
                <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
                  <Raqam
                    nom={t("kuzatuv.xarid_bosimi")}
                    qiymat={
                      bozor.xaridBosimi === null ? null : `${bozor.xaridBosimi}%`
                    }
                  />
                  <Raqam
                    nom={t("kuzatuv.yirik_savdo")}
                    qiymat={String(bozor.yirikSavdo)}
                  />
                  <Raqam
                    nom={t("kuzatuv.hajm_oyna")}
                    qiymat={pul(bozor.hajmUsd)}
                  />
                </div>
                {bozor.xaridBosimi !== null ? (
                  <div className="bg-past/25 mt-3 h-2 overflow-hidden rounded-full">
                    <div
                      className="bg-yaxshi h-full"
                      style={{ width: `${bozor.xaridBosimi}%` }}
                    />
                  </div>
                ) : null}
              </Card>
            </>
          ) : null}

          <JonliStakan
            symbol={coin.symbol}
            matnlar={{
              stakan: t("kuzatuv.stakan"),
              lenta: t("kuzatuv.lenta"),
              xarid: t("kuzatuv.xarid"),
              sotish: t("kuzatuv.sotish"),
              ulanmoqda: t("kuzatuv.ulanmoqda"),
              uzildi: t("kuzatuv.uzildi"),
              narx: t("kuzatuv.narx"),
              miqdor: t("kuzatuv.miqdor"),
              jonliNarx: t("kuzatuv.jonli_narx"),
              yiriklarRoyxat: t("kuzatuv.yiriklar_royxat"),
              yirikYoq: t("kuzatuv.yirik_yoq"),
            }}
            yiriklar={bozor?.yiriklar ?? []}
          />
          <p className="text-matn-past mt-2 text-xs">{t("kuzatuv.jonli_izoh")}</p>
        </>
      ) : (
        <Card>
          <p className="text-matn-past text-sm">{t("kuzatuv.jonli_yoq")}</p>
        </Card>
      )}

      <p className="text-matn-past mt-6 text-xs">{t("kuzatuv.tavsiya_emas")}</p>
    </>
  );
}

function BlokKartasi({
  blok,
  t,
}: {
  blok: KuzatuvBlok;
  t: (kalit: string) => string;
}) {
  const rang = blokRangi(blok);
  return (
    <div
      className={cn(
        "rounded-kartochka bg-panel border p-3",
        rang === "yaxshi"
          ? "border-yaxshi/60"
          : rang === "past"
            ? "border-matn-past/30"
            : "border-ramka-yumshoq opacity-70",
      )}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-sm font-semibold">
          <Ikonka
            nom={BLOK_IKONKASI[blok.nom] ?? "malumot"}
            className={cn(
              "h-4 w-4",
              rang === "yaxshi" ? "text-yaxshi" : "text-matn-past",
            )}
          />
          {BLOK_KALITI[blok.nom] ? t(BLOK_KALITI[blok.nom]) : blok.nom}
        </p>
        <span
          className={cn(
            "text-xs tabular-nums",
            rang === "yaxshi" ? "text-yaxshi" : "text-matn-past",
          )}
        >
          {blok.olchanmadi ? "—" : `${blok.kuch}/${blok.maxraj}`}
        </span>
      </div>

      {blok.tosiq ? <p className="text-ortacha mb-2 text-xs">{blok.tosiq}</p> : null}
      {blok.nom === "Fundamental" && !blok.olchanmadi ? (
        <p className="text-matn-past mb-2 text-[11px]">
          {t("kuzatuv.fundamental_izoh")}
        </p>
      ) : null}
      {blok.olchanmadi ? (
        <p className="text-matn-past text-xs">{t("kuzatuv.blok_olchanmadi")}</p>
      ) : (
        <ul className="space-y-1">
          {blok.tekshiruvlar.map((tek, i) => {
            // ALTERNATIV BILAN QUTQARILGAN blok alohida ko'rinadi
            // (5.3-qism: "qaysi usul ishlagani ko'rsatiladi").
            // Pythonda u `alternativ:<nom>` degan tekshiruv bo'lib
            // qo'shiladi.
            const alt = tek.nom.startsWith("alternativ:");
            return (
            <li key={`${tek.nom}-${i}`} className="flex items-start gap-2 text-xs">
              {/* Belgi — SEGMENT INDIKATORI bilan bir xil shakl.
                  Ilgari bu yerda matnli tasdiq va rad belgilari
                  turardi. Ular loyihaning "interfeysda emoji yo'q"
                  qoidasini buzardi: bunday belgilar har platformada
                  boshqacha chiziladi va palitramizga bo'ysunmaydi.
                  Loyihaning o'z testi buni ushladi. */}
              <span
                aria-hidden
                className={cn(
                  "mt-1 h-2.5 w-2.5 shrink-0 rounded-[2px] border",
                  tek.holat === "ha"
                    ? "border-yaxshi bg-yaxshi"
                    : tek.holat === "yoq"
                      ? "border-past/60"
                      : "border-ramka-yumshoq opacity-40",
                )}
              />
              <span
                className={cn(
                  "min-w-0 flex-1",
                  alt ? "text-sarlavha" : "text-matn-past",
                )}
              >
                {alt ? `${t("kuzatuv.alternativ")}: ` : ""}
                {tek.izoh || tek.nom}
              </span>
            </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}


/** Bitta raqam — nomi ustida, kichik. */
function Raqam({ nom, qiymat }: { nom: string; qiymat: string | null }) {
  return (
    <div>
      <p className="text-matn-past text-[11px]">{nom}</p>
      <p className="tabular-nums">{qiymat ?? "—"}</p>
    </div>
  );
}



/** Blok -> HCS ikonka tizimidagi nom (5.3-qism: "IKONKA bilan").
 *
 * Emoji EMAS: u har platformada boshqacha chiziladi va loyihaning
 * palitrasiga bo'ysunmaydi (`ui/Ikonka.tsx` dagi qoida). */
const BLOK_IKONKASI: Record<string, IkonkaNomi> = {
  Fundamental: "malumot",
  Struktura: "trend",
  "Zona Sifati": "kirish_zonasi",
  Tasdiqlash: "tasdiq",
};

/** Narx darajasi — kichik coinlar uchun ko'proq raqam kerak. */
function daraja(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  return x >= 1 ? `$${x.toFixed(2)}` : `$${x.toPrecision(4)}`;
}
