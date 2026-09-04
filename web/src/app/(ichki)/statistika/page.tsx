import Link from "next/link";

import { Qulf } from "@/components/ui/Qulf";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { cn } from "@/lib/cn";
import { env } from "@/lib/env";
import { tarjimon } from "@/lib/i18n";
import { statistika, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";
import { hozir } from "@/lib/vaqt";

export const dynamic = "force-dynamic";

const DAVRLAR = [
  { kod: "7", kunlar: 7, kalit: "statistika.hafta" },
  { kod: "30", kunlar: 30, kalit: "statistika.oy" },
  { kod: "hammasi", kunlar: null, kalit: "statistika.hammasi" },
] as const;

export default async function Statistika({
  searchParams,
}: {
  searchParams: Promise<{ davr?: string }>;
}) {
  const { til, tarif } = await kirim();
  const t = tarjimon(til);
  if (!tarifQamraydi(tarif, "lite")) {
    return (
      <>
        <Sarlavha matn={t("statistika.sarlavha")} />
        <Qulf til={til} kerakliTarif="lite" botUsername={env().botUsername} />
      </>
    );
  }

  const { davr } = await searchParams;
  const tanlangan = DAVRLAR.find((d) => d.kod === davr) ?? DAVRLAR[1];
  const hozirgi = await hozir();
  const since =
    tanlangan.kunlar === null
      ? null
      : new Date(hozirgi.getTime() - tanlangan.kunlar * 86_400_000)
          .toISOString()
          .slice(0, 10);

  const s = statistika(since);

  // Muvaffaqiyat: TP olganlar / yakunlangan savdolar. Ochiq signallar
  // hisobga kirmaydi — ular hali natija bermagan, ularni qo'shsak
  // ko'rsatkich sun'iy ravishda past chiqadi.
  const yakunlangan = s.tp1Count + s.tp2Count + s.stopCount;
  const winrate = yakunlangan
    ? ((s.tp1Count + s.tp2Count) / yakunlangan) * 100
    : null;

  return (
    <>
      <Sarlavha
        matn={t("statistika.sarlavha")}
        izoh={t("statistika.izoh")}
        ong={
          <div className="flex gap-1">
            {DAVRLAR.map((d) => (
              <Link
                key={d.kod}
                href={`/statistika?davr=${d.kod}`}
                className={cn(
                  "rounded-kichik border px-2.5 py-1 text-xs transition",
                  d.kod === tanlangan.kod
                    ? "border-ramka text-sarlavha font-semibold"
                    : "text-matn-past hover:text-sarlavha border-transparent",
                )}
              >
                {t(d.kalit)}
              </Link>
            ))}
          </div>
        }
      />

      {s.signalsCreated === 0 ? (
        <Card>
          <p className="text-matn-past text-sm">{t("statistika.yoq")}</p>
        </Card>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Katak
              nom={t("statistika.jami")}
              qiymat={String(s.signalsCreated)}
            />
            <Katak
              nom={t("statistika.winrate")}
              qiymat={winrate === null ? "—" : `${winrate.toFixed(0)}%`}
              tone={winrate !== null && winrate >= 50 ? "yaxshi" : "past"}
            />
            <Katak
              nom={t("statistika.tp2")}
              qiymat={String(s.tp2Count)}
              tone="yaxshi"
            />
            <Katak
              nom={t("statistika.stop")}
              qiymat={String(s.stopCount)}
              tone="past"
            />
          </div>

          <Card>
            <CardTitle>{t("statistika.sarlavha")}</CardTitle>
            <dl className="mt-3 space-y-2">
              <Qator
                nom={t("statistika.yopilgan")}
                qiymat={String(yakunlangan)}
              />
              <Qator nom={t("statistika.tp1")} qiymat={String(s.tp1Count)} />
              <Qator
                nom={t("statistika.yolgon")}
                qiymat={String(s.falseSignalCount)}
              />
              <Qator
                nom={t("statistika.ortacha_ball")}
                qiymat={
                  s.averageScore === null ? "—" : s.averageScore.toFixed(1)
                }
              />
              <Qator
                nom={t("signal.nisbat")}
                qiymat={
                  s.averageRiskReward === null
                    ? "—"
                    : `1 : ${s.averageRiskReward.toFixed(2)}`
                }
              />
            </dl>
            <CardHint className="mt-3">
              {t("statistika.davr")}: {t(tanlangan.kalit)}
            </CardHint>
          </Card>
        </div>
      )}
    </>
  );
}

function Katak({
  nom,
  qiymat,
  tone,
}: {
  nom: string;
  qiymat: string;
  tone?: "yaxshi" | "past";
}) {
  const rang =
    tone === "yaxshi"
      ? "text-yaxshi"
      : tone === "past"
        ? "text-past"
        : "text-sarlavha";
  return (
    <div className="border-ramka-yumshoq bg-panel rounded-kartochka border p-3.5">
      <p className="text-matn-past text-xs">{nom}</p>
      <p className={`raqam mt-1 text-2xl font-bold ${rang}`}>{qiymat}</p>
    </div>
  );
}

function Qator({ nom, qiymat }: { nom: string; qiymat: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-white/5 pb-2 text-sm last:border-0">
      <dt className="text-matn-past">{nom}</dt>
      <dd className="raqam font-semibold">{qiymat}</dd>
    </div>
  );
}
