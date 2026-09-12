import Link from "next/link";
import { notFound } from "next/navigation";

import { JonliStakan } from "@/components/kuzatuv/JonliStakan";
import { Segmentlar } from "@/components/kuzatuv/Segmentlar";
import { Card } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { cn } from "@/lib/cn";
import { tarjimon } from "@/lib/i18n";
import { BLOK_KALITI, SEGMENT_KALITI, blokRangi, type KuzatuvBlok } from "@/lib/kuzatuv";
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
            <Card className="mb-3">
              <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
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
                <Raqam nom={t("kuzatuv.market_cap")} qiymat={pul(bozor.marketCap)} />
                <Raqam nom={t("kuzatuv.hajm_24s")} qiymat={pul(bozor.hajm24s)} />
              </div>
              <div className="border-ramka-yumshoq mt-3 grid grid-cols-3 gap-3 border-t pt-3 text-sm">
                <Raqam nom={t("kuzatuv.soat_1")} qiymat={foiz(bozor.ozgarish1s)} />
                <Raqam nom={t("kuzatuv.soat_24")} qiymat={foiz(bozor.ozgarish24s)} />
                <Raqam nom={t("kuzatuv.kun_7")} qiymat={foiz(bozor.ozgarish7k)} />
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
            }}
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
        <p className="text-sm font-semibold">
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
      {blok.olchanmadi ? (
        <p className="text-matn-past text-xs">{t("kuzatuv.blok_olchanmadi")}</p>
      ) : (
        <ul className="space-y-1">
          {blok.tekshiruvlar.map((tek, i) => (
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
              <span className="text-matn-past min-w-0 flex-1">{tek.izoh || tek.nom}</span>
            </li>
          ))}
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

/** $1.2B ko'rinishida. `null` — "ma'lumot yo'q", nol EMAS. */
function pul(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  const birliklar: [number, string][] = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [chegara, belgi] of birliklar) {
    if (Math.abs(x) >= chegara) return `$${(x / chegara).toFixed(2)}${belgi}`;
  }
  return `$${x.toFixed(2)}`;
}

function foiz(x: number | null): string | null {
  if (x === null || !Number.isFinite(x)) return null;
  return `${x > 0 ? "+" : ""}${x.toFixed(2)}%`;
}
