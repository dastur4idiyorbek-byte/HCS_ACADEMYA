import { notFound, redirect } from "next/navigation";

import { Grafik } from "@/components/Grafik";
import { Himoya } from "@/components/Himoya";
import { Kalkulyator } from "@/components/Kalkulyator";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { botHavolasi, env } from "@/lib/env";
import { HOLAT_BELGISI, holatNomi, narx, riskFoyda, sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { kirishMumkin, signalOl, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function SignalSahifasi({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { til, tarif, foydalanuvchi } = await kirim();
  const t = tarjimon(til);
  if (!tarifQamraydi(tarif, "lite")) redirect("/signallar");

  const { id } = await params;
  const signal = signalOl(Number(id));
  if (!signal) notFound();

  // Kech qolgan signalning narxlari ochilmaydi — ro'yxatdagi qoida
  // shu yerda ham amal qiladi, aks holda manzilni qo'lda yozib
  // ochib olish mumkin bo'lardi.
  if (!kirishMumkin(signal.status)) redirect("/signallar");

  const rr = riskFoyda(signal.entry, signal.stop, signal.tp2);
  // Suv belgisida ID turadi: skrinshot tarqalsa, u kimdan chiqqani ko'rinadi
  const suvBelgisi = `HCS · ${foydalanuvchi?.telegramId ?? "—"}`;
  const buyurtma = signal.entryOrderType === "market" ? "signal.market" : "signal.limit";

  return (
    <>
      <Sarlavha
        matn={`${HOLAT_BELGISI[signal.status]} ${signal.symbol}`}
        izoh={holatNomi(signal.status, til)}
        ong={
          signal.score !== null ? (
            <Badge tone="yaxshi">
              {signal.score.toFixed(0)} {t("umumiy.ball")}
            </Badge>
          ) : undefined
        }
      />

      <div className="space-y-5">
<Himoya belgi={suvBelgisi} ogohlantirish={t("signal.himoya")}>
          <Card variant="urgu">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
              <Qiymat nom={t("signal.entry")} qiymat={narx(signal.entry)} />
              <Qiymat nom={t("signal.stop")} qiymat={narx(signal.stop)} tone="past" />
              <Qiymat nom={t("signal.tp1")} qiymat={narx(signal.tp1)} tone="yaxshi" />
              <Qiymat nom={t("signal.tp2")} qiymat={narx(signal.tp2)} tone="yaxshi" />
            </dl>
            <div className="mt-4 border-t border-white/10 pt-3">
              <p className="text-sm">
                {signal.entryOrderType === "market" ? "⚡" : "📌"} {t(buyurtma)}
              </p>
            </div>
          </Card>
        </Himoya>

        <p className="text-matn-past px-1 text-xs leading-relaxed">
          🔒 {t("signal.himoya_izoh")}
        </p>

        <div className="grid gap-5 sm:grid-cols-2">
          <Card>
            <CardTitle>{t("signal.nisbat")}</CardTitle>
            <p className="raqam text-sarlavha mt-2 text-2xl font-bold">
              {rr === null ? "—" : `1 : ${rr.toFixed(2)}`}
            </p>
            <CardHint>
              {t("signal.berilgan")}: {sana(signal.createdAt)} UTC
            </CardHint>
            {signal.marketHealthAtEntry !== null && (
              <CardHint>
                {t("salomatlik.sarlavha")}: {signal.marketHealthAtEntry.toFixed(0)}/100
              </CardHint>
            )}
          </Card>

          <Card>
            <CardTitle>{t("signal.halol_sabab")}</CardTitle>
            <p className="mt-2 text-sm leading-relaxed">
              {signal.halalReason ?? t("umumiy.yoq")}
            </p>
          </Card>
        </div>

        <Card>
          <CardTitle>📈 {t("signal.grafik")}</CardTitle>
          <div className="mt-3">
            <Grafik
              symbol={`BINANCE:${signal.symbol}`}
              xatoMatni={t("signal.grafik_xato")}
            />
          </div>
        </Card>

        {/* Kalkulyator HIMOYA ICHIDA: unda kirish, Stop va TP narxlari
            turadi — ya'ni signalning o'zi. Grafik esa tashqarida, chunki
            u ochiq bozor ma'lumoti. */}
        <Himoya belgi={suvBelgisi} ogohlantirish={t("signal.himoya")}>
          <Kalkulyator
            symbol={signal.symbol}
            entry={signal.entry}
            stop={signal.stop}
            tpNarxlari={[signal.tp1, signal.tp2]}
            matnlar={{
              sarlavha: t("signal.kalk_sarlavha"),
              summa: t("signal.kalk_summa"),
              kirish: t("signal.kalk_kirish"),
              stop: t("signal.kalk_stop"),
              ulush: t("signal.kalk_ulush"),
              umumiy: t("signal.kalk_umumiy"),
              stop_agar: t("signal.kalk_stop_agar"),
              jami: t("signal.kalk_jami"),
              ulush_xato: t("signal.kalk_ulush_xato"),
              ogohlantirish: t("signal.kalk_ogohlantirish"),
            }}
          />
        </Himoya>

        <Card>
          <CardTitle>{t("signal.ball_sabab")}</CardTitle>
          <BallTafsiloti xom={signal.scoreBreakdown} bosh={t("umumiy.yoq")} />
        </Card>

        <Card>
          <CardHint>{t("kontent.botda_izoh")}</CardHint>
          <div className="mt-3 flex flex-wrap gap-3">
            <Button href={botHavolasi(env().botUsername, "start")} variant="ikkilamchi">
              Telegram
            </Button>
            <Button href="/signallar" variant="shaffof">
              {t("umumiy.orqaga")}
            </Button>
          </div>
        </Card>
      </div>
    </>
  );
}

function Qiymat({
  nom,
  qiymat,
  tone,
}: {
  nom: string;
  qiymat: string;
  tone?: "yaxshi" | "past";
}) {
  const rang = tone === "yaxshi" ? "text-yaxshi" : tone === "past" ? "text-past" : "text-sarlavha";
  return (
    <div>
      <dt className="text-matn-past text-xs uppercase tracking-wide">{nom}</dt>
      <dd className={`raqam mt-0.5 font-semibold ${rang}`}>{qiymat}</dd>
    </div>
  );
}

/** Ball tafsiloti bazada JSON matn sifatida saqlanadi.
 *
 * Uni ko'r-ko'rona `JSON.parse` qilib bo'lmaydi: formati o'zgargan yoki
 * eski yozuv bo'lsa, butun sahifa yiqiladi. Xato bo'lsa xom matn
 * ko'rsatiladi — ma'lumot yo'qolmaydi, sahifa esa ishlayveradi (0.3-band).
 */
function BallTafsiloti({ xom, bosh }: { xom: string | null; bosh: string }) {
  if (!xom) return <p className="text-matn-past mt-2 text-sm">{bosh}</p>;

  let tahlil: Record<string, unknown> | null = null;
  try {
    const natija = JSON.parse(xom);
    if (natija && typeof natija === "object" && !Array.isArray(natija)) {
      tahlil = natija as Record<string, unknown>;
    }
  } catch {
    tahlil = null;
  }

  if (!tahlil) {
    return (
      <pre className="text-matn-past mt-2 overflow-x-auto text-xs whitespace-pre-wrap">{xom}</pre>
    );
  }

  return (
    <dl className="mt-3 space-y-1.5">
      {Object.entries(tahlil).map(([kalit, qiymat]) => (
        <div key={kalit} className="flex items-baseline justify-between gap-3 text-sm">
          <dt className="text-matn-past">{kalit}</dt>
          <dd className="raqam font-medium">
            {typeof qiymat === "number" ? qiymat.toFixed(2) : String(qiymat)}
          </dd>
        </div>
      ))}
    </dl>
  );
}
