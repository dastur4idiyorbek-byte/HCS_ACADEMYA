import { SalomatlikShkalasi, SalomatlikYoq } from "@/components/Salomatlik";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { bosqichNomi, vaqtDarvozasimi, voronkaTartibi } from "@/lib/bosqichlar";
import { salomatlikBandlari } from "@/lib/config";
import { davr, keyingiDavr } from "@/lib/davr";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { ballStatistikasi, salomatlikOxirgi, salomatlikTarixi, voronka } from "@/lib/queries";
import { kirim } from "@/lib/session";
import { hozir } from "@/lib/vaqt";

export const dynamic = "force-dynamic";

const SOATLAR = 24;

/** Omil balli — bazada 0..1, ekranda foiz.
 *
 * SHKALA MOS KELMASLIGI (1-naqsh). Bot `HealthFactor.score` ni
 * o'zgartirmasdan yozadi, ya'ni 0..1 oralig'ida. Sahifa esa uni
 * to'g'ridan-to'g'ri foiz deb chizardi: haqiqiy ma'lumotda har bir
 * omil "0" yoki "1" bo'lib ko'rinardi va chiziqchalar deyarli bo'sh
 * turardi. Buni demo ma'lumot yashirgan edi — u 0-100 shkalada
 * yozilgani uchun ekran to'g'ri ko'rinardi.
 */
function omilFoizi(ball: number): number {
  return Math.round(Math.min(1, Math.max(0, ball)) * 100);
}

/** Bozor Salomatligi va "nega signal yo'q" BIR SAHIFADA.
 *
 * Ilgari ular ikki alohida menyu bandi edi. Amalda esa bitta savolning
 * ikki yarmi: "bozor qanday?" va "shuning uchun bugun nima bo'ldi?".
 * Ajratilgan holda foydalanuvchi ikkinchisini topmasdi ham.
 */
export default async function Salomatlik() {
  const { til } = await kirim();
  const t = tarjimon(til);

  const salomatlik = salomatlikOxirgi();
  const tarix = salomatlikTarixi(8);
  const bandlar = salomatlikBandlari();

  const boshlanish = new Date((await hozir()).getTime() - SOATLAR * 60 * 60 * 1000);
  const barchasi = voronka(boshlanish);
  const ballStat = ballStatistikasi(boshlanish);

  // Vaqt darvozalari ajratiladi: ular har siklda, har coin uchun yoziladi
  // va foizni butunlay buzadi (docs/ARXITEKTURA.md, ROUTINE_STAGES).
  const haqiqiy = barchasi
    .filter((q) => !vaqtDarvozasimi(q.stage))
    .sort((a, b) => voronkaTartibi(a.stage) - voronkaTartibi(b.stage));
  const darvozalar = barchasi.filter((q) => vaqtDarvozasimi(q.stage));

  const jami = haqiqiy.reduce((s, q) => s + q.count, 0);
  const eng = haqiqiy.reduce((m, q) => Math.max(m, q.count), 0);

  // Tartib — VAZN bo'yicha, og'iridan yengiliga. Struktura kengligi
  // birinchi: u indeksning asosiy omili (45).
  //
  // EMA asosidagi "Trend kengligi" olib tashlandi (58-bo'lim): u aynan
  // SHU savolni ("nechta coin ko'tarilishda") o'lchardi, faqat
  // kechikuvchi vosita bilan. Eski yozuvlarda ustun qoladi, lekin
  // ekranda ko'rsatilmaydi — ikki xil raqam chalkashtirardi.
  const omillar = salomatlik
    ? [
        { kalit: "salomatlik.struktura", qiymat: salomatlik.structureBreadthScore },
        { kalit: "salomatlik.sigim", qiymat: salomatlik.userCapacityScore },
        { kalit: "salomatlik.volatillik", qiymat: salomatlik.volatilityScore },
        { kalit: "salomatlik.toyinganlik", qiymat: salomatlik.saturationScore },
        { kalit: "salomatlik.dominatsiya", qiymat: salomatlik.btcDominanceScore },
        { kalit: "salomatlik.davr", qiymat: salomatlik.quarterlyPhaseScore },
      ].filter((o) => o.qiymat !== null)
    : [];

  // QT davri indeks HISOBLANGAN paytga qarab aniqlanadi, "hozir" ga
  // emas: shkala o'sha lahzaning surati, ikkalasi bir vaqtga tegishli
  // bo'lishi kerak.
  const joriyDavr = salomatlik?.createdAt ? davr(salomatlik.createdAt) : null;

  return (
    <>
      <Sarlavha matn={`📊 ${t("salomatlik.sarlavha")}`} />

      <div className="space-y-5">
        <Card variant="urgu">
          <p className="text-sm leading-relaxed">{t("salomatlik.sahifa_kirish")}</p>
          <div className="mt-5">
            {salomatlik ? (
              <SalomatlikShkalasi
                qiymat={salomatlik.value}
                band={salomatlik.band}
                bandlar={bandlar}
                til={til}
              />
            ) : (
              <SalomatlikYoq til={til} />
            )}
          </div>
          {joriyDavr && (
            <div className="border-ramka/40 mt-4 border-t pt-3">
              <p className="text-sm">
                <span aria-hidden>🗓️ </span>
                <span className="text-matn-past">{t("salomatlik.davr_sarlavha")}: </span>
                <span className="text-sarlavha font-semibold">
                  {t(`salomatlik.davr_${joriyDavr}`)}
                </span>
              </p>
              <p className="text-matn-past mt-1 text-xs">
                {t("salomatlik.davr_keyingi")}: {keyingiDavr(joriyDavr)} · {" "}
                {t("salomatlik.davr_izoh")}
              </p>
            </div>
          )}
          {salomatlik?.createdAt && (
            <p className="text-matn-past mt-3 text-center text-xs">
              {t("umumiy.yangilangan")}: {sana(salomatlik.createdAt)} UTC
            </p>
          )}
        </Card>

        {omillar.length > 0 && (
          <Card>
            <CardTitle>{t("salomatlik.omillar")}</CardTitle>
            <ul className="mt-3 space-y-2">
              {omillar.map((o) => (
                <li key={o.kalit} className="flex items-center gap-3">
                  <span className="w-40 shrink-0 text-sm">{t(o.kalit)}</span>
                  <span className="bg-fon h-2 flex-1 overflow-hidden rounded-full">
                    <span
                      className="bg-yaxshi block h-full rounded-full"
                      style={{ width: `${omilFoizi(o.qiymat!)}%` }}
                    />
                  </span>
                  <span className="raqam text-matn-past w-10 text-right text-xs">
                    {omilFoizi(o.qiymat!)}%
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {tarix.length > 1 && (
          <Card>
            <CardTitle>{t("salomatlik.tarix")}</CardTitle>
            <ul className="mt-3 space-y-1.5">
              {tarix.map((h, i) => (
                <li key={i} className="flex items-center gap-3 text-xs">
                  <span className="text-matn-past raqam w-32 shrink-0">
                    {sana(h.createdAt)}
                  </span>
                  <span className="bg-fon h-1.5 flex-1 overflow-hidden rounded-full">
                    <span
                      className="bg-yaxshi block h-full rounded-full"
                      style={{ width: `${Math.min(100, Math.max(0, h.value))}%` }}
                    />
                  </span>
                  <span className="raqam w-10 text-right font-semibold">
                    {h.value.toFixed(1)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* Ajratuvchi: shkala tugadi, endi voronka boshlanadi */}
        <div className="border-ramka/50 flex items-center gap-3 border-t pt-6">
          <span className="text-sarlavha text-lg font-bold">
            🔇 {t("salomatlik.voronka_sarlavha")}
          </span>
        </div>

        <Card>
          <p className="text-sm leading-relaxed">{t("salomatlik.voronka_kirish")}</p>
        </Card>

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
