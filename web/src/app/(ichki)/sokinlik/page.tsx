import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { bosqichNomi, vaqtDarvozasimi, voronkaTartibi } from "@/lib/bosqichlar";
import { tarjimon } from "@/lib/i18n";
import { ballStatistikasi, voronka } from "@/lib/queries";
import { kirim } from "@/lib/session";
import { hozir } from "@/lib/vaqt";

export const dynamic = "force-dynamic";

const SOATLAR = 24;

export default async function Sokinlik() {
  const { til } = await kirim();
  const t = tarjimon(til);

  const boshlanish = new Date((await hozir()).getTime() - SOATLAR * 60 * 60 * 1000);
  const barchasi = voronka(boshlanish);
  const ballStat = ballStatistikasi(boshlanish);

  // Vaqt darvozalari ajratiladi: ular har siklda, har coin uchun
  // yoziladi va foizni butunlay buzadi (docs/ARXITEKTURA.md, ROUTINE_STAGES).
  const haqiqiy = barchasi
    .filter((q) => !vaqtDarvozasimi(q.stage))
    .sort((a, b) => voronkaTartibi(a.stage) - voronkaTartibi(b.stage));
  const darvozalar = barchasi.filter((q) => vaqtDarvozasimi(q.stage));

  const jami = haqiqiy.reduce((s, q) => s + q.count, 0);
  const eng = haqiqiy.reduce((m, q) => Math.max(m, q.count), 0);

  return (
    <>
      <Sarlavha matn={t("sokinlik.sarlavha")} izoh={t("sokinlik.izoh")} />

      <div className="space-y-5">
        {haqiqiy.length === 0 ? (
          <Card>
            <p className="text-matn-past text-sm">{t("sokinlik.yoq")}</p>
          </Card>
        ) : (
          <Card variant="urgu">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>{t("sokinlik.davr")}</CardTitle>
              <Badge>
                {jami} {t("sokinlik.nomzod").toLowerCase()}
              </Badge>
            </div>

            <ol className="mt-4 space-y-3">
              {haqiqiy.map((q, i) => {
                // Chapdan o'ngga (ro'yxatda pastga) rang to'yinganligi
                // kamayadi: bosqich qanchalik "qattiq" bo'lsa, shunchalik
                // kam nomzod o'tganini ko'rsatadi.
                const toyinganlik = Math.max(0.25, 1 - i / Math.max(1, haqiqiy.length - 1));
                const kenglik = eng ? Math.max(4, (q.count / eng) * 100) : 4;
                return (
                  <li key={q.stage}>
                    <div className="mb-1 flex items-baseline justify-between gap-3">
                      <span className="text-sm">
                        <span className="text-matn-past mr-1.5">{i + 1}.</span>
                        {bosqichNomi(q.stage)}
                      </span>
                      <span className="raqam shrink-0 text-sm font-semibold">
                        {q.count}
                        <span className="text-matn-past ml-1 text-xs">
                          {jami ? `· ${((q.count / jami) * 100).toFixed(0)}%` : ""}
                        </span>
                      </span>
                    </div>
                    <div className="bg-fon h-2.5 overflow-hidden rounded-full">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${kenglik}%`,
                          background: "var(--rang-yaxshi)",
                          opacity: toyinganlik,
                        }}
                      />
                    </div>
                  </li>
                );
              })}
            </ol>
          </Card>
        )}

        {ballStat && (
          <Card>
            <CardTitle>{t("sokinlik.ball_stat")}</CardTitle>
            <dl className="mt-3 grid grid-cols-3 gap-3">
              <Raqam nom={t("sokinlik.nomzod")} qiymat={String(ballStat.soni)} />
              <Raqam nom={t("sokinlik.eng_yuqori")} qiymat={ballStat.engYuqori.toFixed(1)} />
              <Raqam nom={t("sokinlik.ortacha")} qiymat={ballStat.ortacha.toFixed(1)} />
            </dl>
            <CardHint className="mt-3">
              Bu raqamlarsiz &laquo;chegara juda balandmi yoki nomzodlar zaifmi&raquo; degan
              savolga javob bo&apos;lmaydi.
            </CardHint>
          </Card>
        )}

        {darvozalar.length > 0 && (
          <Card>
            <CardTitle>⏱ {t("sokinlik.vaqt_izoh")}</CardTitle>
            <ul className="mt-3 space-y-1.5">
              {darvozalar.map((q) => (
                <li key={q.stage} className="flex justify-between gap-3 text-sm">
                  <span className="text-matn-past">{bosqichNomi(q.stage)}</span>
                  <span className="raqam">{q.count}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </>
  );
}

function Raqam({ nom, qiymat }: { nom: string; qiymat: string }) {
  return (
    <div className="border-ramka-yumshoq rounded-kichik border p-3">
      <dt className="text-matn-past text-xs">{nom}</dt>
      <dd className="raqam text-sarlavha mt-1 text-xl font-bold">{qiymat}</dd>
    </div>
  );
}
