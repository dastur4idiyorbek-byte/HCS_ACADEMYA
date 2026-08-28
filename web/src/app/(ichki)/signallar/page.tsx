import Link from "next/link";

import { Himoya } from "@/components/Himoya";
import { JonliNarx } from "@/components/JonliNarx";
import { SignalOchish } from "@/components/SignalOchish";
import { Qulf } from "@/components/ui/Qulf";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { kotirovka, tp1Ulushi } from "@/lib/config";
import { hajmTaklifi } from "@/lib/hajm";
import { birjaJuftligi } from "@/lib/kalkulyator";
import { env } from "@/lib/env";
import { HOLAT_BELGISI, holatNomi, narx } from "@/lib/format";
import { kalkulyatorMatnlari, tarjimon } from "@/lib/i18n";
import { kirishMumkin, signallar, tarifQamraydi, yopilgan } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function Signallar() {
  const { til, tarif, foydalanuvchi } = await kirim();
  const t = tarjimon(til);

  // Obuna tekshiruvi ma'lumot O'QILISHIDAN OLDIN: qulflangan sahifaning
  // HTML manbasida narxlar qolib ketmasligi kerak.
  if (!tarifQamraydi(tarif, "lite")) {
    return (
      <>
        <Sarlavha matn={t("signal.sarlavha")} />
        <Qulf til={til} kerakliTarif="lite" botUsername={env().botUsername} />
      </>
    );
  }

  const balans = foydalanuvchi?.declaredBalanceUsd ?? null;
  const royxat = signallar(100);
  const suvBelgisi = `HCS · ${foydalanuvchi?.telegramId ?? "—"}`;
  const ochiladigan = royxat.filter((s) => kirishMumkin(s.status));
  const kech = royxat.filter((s) => !kirishMumkin(s.status) && !yopilgan(s.status));
  const arxiv = royxat.filter((s) => yopilgan(s.status));

  if (royxat.length === 0) {
    return (
      <>
        <Sarlavha matn={t("signal.sarlavha")} />
        <Card>
          <CardTitle>🤫 {t("signal.yoq")}</CardTitle>
          <div className="mt-4">
            <Button href="/salomatlik" variant="ikkilamchi">
              {t("signal.nega_yoq")}
            </Button>
          </div>
        </Card>
      </>
    );
  }

  return (
    <>
      <Sarlavha matn={t("signal.sarlavha")} />

      <div className="space-y-6">
        <Guruh sarlavha={t("signal.faol")} bosh>
          {/* Har bir faol signal — o'z kartochkasi. Grafik va kalkulyator
              SHU YERDA ochiladi: avval ular faqat signal ichiga kirilganda
              ko'rinardi va topilmay qolardi. Yopiq holatda widget DOM da
              yo'q — uchta signal uchta iframe yuklamasin. */}
          {ochiladigan.map((s) => (
            <div
              key={s.id}
              className="border-ramka bg-panel rounded-kartochka border p-3.5"
            >
              <Himoya belgi={suvBelgisi} ogohlantirish={t("signal.himoya")}>
                <Link
                  href={`/signallar/${s.id}`}
                  className="hover:bg-panel-yorqin rounded-tugma -m-1.5 flex items-center gap-3 p-1.5 transition"
                >
                  <span aria-hidden className="text-lg">
                    {HOLAT_BELGISI[s.status]}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="text-sarlavha block font-semibold">{s.symbol}</span>
                    <span className="text-matn-past raqam block text-xs">
                      {t("signal.entry")} {narx(s.entry)} · {holatNomi(s.status, til)}
                    </span>
                  </span>
                  {/* Kirishdan qancha yurgani — YASHIL/QIZIL foiz. Avval
                      kartochka faqat "Faol" derdi va signal foydaga
                      ketayotganini yoki zarar tomon yurayotganini
                      ko'rsatmasdi. Yangi foydalanuvchi uchun birinchi
                      savol aynan shu. */}
                  <span className="text-right">
                    <JonliNarx
                      juftlik={birjaJuftligi(s.symbol, kotirovka())}
                      kirish={s.entry}
                      qisqa
                    />
                  </span>
                  {s.score !== null && (
                    <Badge tone="yaxshi">
                      {s.score.toFixed(0)} {t("umumiy.ball")}
                    </Badge>
                  )}
                  <span aria-hidden className="text-matn-past">
                    ›
                  </span>
                </Link>
              </Himoya>

              <SignalOchish
                symbol={s.symbol}
                entry={s.entry}
                stop={s.stop}
                tpNarxlari={[s.tp1, s.tp2]}
                belgi={suvBelgisi}
                kotirovka={kotirovka()}
                tp1Ulush={tp1Ulushi()}
                buyurtmaMatni={`${s.entryOrderType === "market" ? "⚡" : "📌"} ${t(
                  s.entryOrderType === "market" ? "signal.market" : "signal.limit",
                )}`}
                berilgan={s.createdAt}
                boshlangichSumma={
                  balans === null ? null : (hajmTaklifi(balans, s.entry, s.stop)?.hajm ?? null)
                }
                matnlar={kalkulyatorMatnlari(t)}
              />
            </div>
          ))}
          {ochiladigan.length === 0 && (
            <p className="text-matn-past text-sm">{t("signal.yoq")}</p>
          )}
        </Guruh>

        {kech.length > 0 && (
          <Guruh sarlavha={t("signal.kech")} izoh={t("signal.kech_izoh")}>
            {kech.map((s) => (
              <KechQator key={s.id} belgi={HOLAT_BELGISI[s.status]} symbol={s.symbol} holat={holatNomi(s.status, til)} />
            ))}
          </Guruh>
        )}

        {arxiv.length > 0 && (
          <Guruh sarlavha={t("signal.yopiq")}>
            {arxiv.slice(0, 20).map((s) => (
              <KechQator
                key={s.id}
                belgi={HOLAT_BELGISI[s.status]}
                symbol={s.symbol}
                holat={holatNomi(s.status, til)}
                natija={s.resultPct}
              />
            ))}
          </Guruh>
        )}
      </div>
    </>
  );
}

function Guruh({
  sarlavha,
  izoh,
  bosh,
  children,
}: {
  sarlavha: string;
  izoh?: string;
  bosh?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className={bosh ? "text-sarlavha mb-3 font-semibold" : "text-matn-past mb-3 text-sm font-semibold uppercase tracking-wide"}>
        {sarlavha}
      </h2>
      {izoh && <CardHint className="mb-3">{izoh}</CardHint>}
      <div className="space-y-2">{children}</div>
    </section>
  );
}

/** Ochilmaydigan qator — ATAYLAB `<Link>` emas.
 *
 * "Kech qolgan" signal ro'yxatdan olib tashlanmaydi (foydalanuvchi u
 * haqda bilishi kerak), lekin narxlari ochilmaydi: kech kirish eng ko'p
 * uchraydigan zarar sababi. Buni foydalanuvchi o'zi hisoblab
 * o'tirmasligi kerak.
 */
function KechQator({
  belgi,
  symbol,
  holat,
  natija,
}: {
  belgi: string;
  symbol: string;
  holat: string;
  natija?: number | null;
}) {
  return (
    <div className="border-ramka-yumshoq rounded-kartochka flex items-center gap-3 border p-3 opacity-70">
      <span aria-hidden>{belgi}</span>
      <span className="flex-1 text-sm font-medium">{symbol}</span>
      <span className="text-matn-past text-xs">{holat}</span>
      {natija !== undefined && natija !== null && (
        <span
          className={`raqam text-xs font-semibold ${natija >= 0 ? "text-yaxshi" : "text-past"}`}
        >
          {natija > 0 ? "+" : ""}
          {natija.toFixed(2)}%
        </span>
      )}
    </div>
  );
}
