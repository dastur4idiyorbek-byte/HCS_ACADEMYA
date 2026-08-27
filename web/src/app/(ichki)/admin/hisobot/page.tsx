import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { hisobotlar } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function Hisobot() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const royxat = hisobotlar(8);
  const oxirgi = royxat[0];

  return (
    <>
      <Sarlavha matn={`🧾 ${t("admin.hisobot")}`} izoh={t("admin.hisobot_izoh")} />

      {!oxirgi ? (
        <Card>
          <p className="text-matn-past text-sm">{t("admin.hisobot_yoq")}</p>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card variant="urgu">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>
                {sana(oxirgi.generatedAt)} UTC
              </CardTitle>
              <Badge>
                {oxirgi.periodDays} {t("admin.davr_kun")}
              </Badge>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Katak nom={t("statistika.jami")} qiymat={String(oxirgi.total)} />
              <Katak nom={t("admin.savdo")} qiymat={String(oxirgi.traded)} />
              <Katak
                nom={t("admin.winrate")}
                qiymat={
                  oxirgi.traded
                    ? `${Math.round(((oxirgi.tp2 + oxirgi.tp1ThenStop) / oxirgi.traded) * 100)}%`
                    : "—"
                }
                tone={
                  oxirgi.traded && (oxirgi.tp2 + oxirgi.tp1ThenStop) / oxirgi.traded >= 0.5
                    ? "yaxshi"
                    : "past"
                }
              />
              <Katak nom={t("statistika.stop")} qiymat={String(oxirgi.stop)} tone="past" />
            </dl>

            <dl className="mt-4 space-y-2 border-t border-white/10 pt-3">
              <Qator nom="🎯🎯 TP2" qiymat={String(oxirgi.tp2)} />
              <Qator nom="🎯 TP1 → Stop" qiymat={String(oxirgi.tp1ThenStop)} />
              <Qator nom={`⛔ ${t("admin.bekor")}`} qiymat={String(oxirgi.cancelled)} />
              <Qator nom={`⚠️ ${t("statistika.yolgon")}`} qiymat={String(oxirgi.falseSignals)} />
              <Qator
                nom={t("statistika.ortacha_ball")}
                qiymat={oxirgi.averageScore === null ? "—" : `${oxirgi.averageScore.toFixed(0)}/100`}
              />
              <Qator
                nom={t("admin.ushlash")}
                qiymat={
                  oxirgi.averageHoldingHours === null
                    ? "—"
                    : `${oxirgi.averageHoldingHours.toFixed(1)} ${t("admin.soat")}`
                }
              />
              <Qator nom={t("admin.naqsh")} qiymat={String(oxirgi.patternCount)} />
            </dl>

            {oxirgi.sampleWarning && (
              <p className="border-ortacha/60 text-ortacha rounded-kichik mt-4 border px-3 py-2 text-sm">
                ℹ️ {oxirgi.sampleWarning}
              </p>
            )}
          </Card>

          <Card>
            <CardTitle>{t("admin.toliq_matn")}</CardTitle>
            <CardHint>
              Bot adminlarga AYNAN shu matnni yuborgan — bu audit izi.
            </CardHint>
            <pre className="text-matn mt-3 overflow-x-auto text-xs leading-relaxed whitespace-pre-wrap">
              {oxirgi.rendered}
            </pre>
          </Card>

          {royxat.length > 1 && (
            <Card>
              <CardTitle>{t("admin.hisobot_tarixi")}</CardTitle>
              <ul className="mt-3 space-y-1.5">
                {royxat.slice(1).map((h) => (
                  <li key={h.id} className="flex justify-between gap-3 text-sm">
                    <span className="text-matn-past raqam">{sana(h.generatedAt)}</span>
                    <span className="raqam">
                      {h.traded} {t("umumiy.dona")} ·{" "}
                      {h.traded
                        ? `${Math.round(((h.tp2 + h.tp1ThenStop) / h.traded) * 100)}%`
                        : "—"}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
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
  const rang = tone === "yaxshi" ? "text-yaxshi" : tone === "past" ? "text-past" : "text-sarlavha";
  return (
    <div className="border-ramka-yumshoq rounded-kichik border p-3">
      <dt className="text-matn-past text-xs">{nom}</dt>
      <dd className={`raqam mt-1 text-xl font-bold ${rang}`}>{qiymat}</dd>
    </div>
  );
}

function Qator({ nom, qiymat }: { nom: string; qiymat: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <dt className="text-matn-past">{nom}</dt>
      <dd className="raqam font-semibold">{qiymat}</dd>
    </div>
  );
}
