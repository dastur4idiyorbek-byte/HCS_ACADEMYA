import { notFound, redirect } from "next/navigation";

import { Grafik } from "@/components/Grafik";
import { Himoya } from "@/components/Himoya";
import { Kalkulyator } from "@/components/Kalkulyator";
import { KirishOgohlantirish } from "@/components/KirishOgohlantirish";
import { SignalKartochka } from "@/components/SignalKartochka";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { kechKirishChegarasi, kotirovka, tpUlushlari } from "@/lib/config";
import { botHavolasi, env } from "@/lib/env";
import { HOLAT_BELGISI, holatNomi, narx, pul } from "@/lib/format";
import { hajmTaklifi } from "@/lib/hajm";
import { kalkulyatorMatnlari, kartochkaMatnlari, tarjimon } from "@/lib/i18n";
import { birjaJuftligi } from "@/lib/kalkulyator";
import { amaldagiStop } from "@/lib/kirish-holati";
import { davomEtmoqda, kirishMumkin, pozitsiyaOl, signalOl, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { kirdim } from "../amallar";

export const dynamic = "force-dynamic";

export default async function SignalSahifasi({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ kirdim?: string; xato?: string }>;
}) {
  const { til, tarif, foydalanuvchi } = await kirim();
  const { kirdim: kirdiMi, xato } = await searchParams;
  const t = tarjimon(til);
  if (!tarifQamraydi(tarif, "lite")) redirect("/signallar");

  const { id } = await params;
  const signal = signalOl(Number(id));
  if (!signal) notFound();

  // YOPILGAN signal ochilmaydi. Lekin TP1 olgan signal YOPILMAGAN:
  // unga kirgan odam uchun u hali jonli va unga Stop kirish narxiga
  // ko'tarilgani, yangilangan grafik va kalkulyator KERAK. Ilgari bu
  // sahifa uni ham ro'yxatga qaytarib yuborardi — ya'ni pozitsiyasi
  // bor odam o'z signalini umuman ko'ra olmasdi.
  if (!davomEtmoqda(signal.status)) redirect("/signallar");

  // Suv belgisida ID turadi: skrinshot tarqalsa, u kimdan chiqqani ko'rinadi
  const suvBelgisi = `HCS · ${foydalanuvchi?.telegramId ?? "—"}`;
  const pozitsiya = foydalanuvchi ? pozitsiyaOl(foydalanuvchi.id, signal.id) : null;
  // Taklif — BOTDAGI hisobning aynan o'zi (`web/src/lib/hajm.ts`).
  // Kalkulyator ham, "Men sotib oldim" ham SHU raqamdan boshlanadi,
  // ya'ni foydalanuvchi bir sahifada ikki xil son ko'rmaydi.
  const balans = foydalanuvchi?.declaredBalanceUsd ?? null;

  // AMALDAGI Stop: TP1 olingach u kirish narxiga ko'tariladi. Bot ham
  // aynan shu darajani kuzatadi (`Signal.effective_stop`), shuning
  // uchun kartochka, kalkulyator va hajm taklifi ham SHU raqamdan
  // hisoblanadi — foydalanuvchi bir sahifada ikki xil Stop ko'rmaydi.
  const stop = amaldagiStop(signal.entry, signal.stop, signal.tp1Reached);
  const yangiKirish = kirishMumkin(signal.status);
  // Hajm tavsiyasi FAQAT yangi kirish ochiq bo'lganda. TP1 dan keyin
  // Stop kirish narxiga teng, ya'ni "xavf puli / Stop masofasi"
  // formulasi ma'nosini yo'qotadi — va bu signalga endi kirilmaydi ham.
  const taklif =
    balans === null || !yangiKirish ? null : hajmTaklifi(balans, signal.entry, stop);
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
        {/* Signalning O'ZI birinchi — avval sahifa avtomatik to'lgan
            kalkulyator maydonlaridan boshlanardi va qaysi raqam
            signalniki ekani bilinmasdi. Tartib: signal -> grafik ->
            kalkulyator. */}
        <Himoya belgi={suvBelgisi} ogohlantirish={t("signal.himoya")}>
          <SignalKartochka
            symbol={signal.symbol}
            kotirovka={kotirovka()}
            entry={signal.entry}
            stop={stop}
            tplar={signal.tplar}
            ulushlar={tpUlushlari(signal.tplar.length)}
            buyurtmaMatni={`${signal.entryOrderType === "market" ? "⚡" : "📌"} ${t(buyurtma)}`}
            berilgan={signal.createdAt}
            matnlar={kartochkaMatnlari(t)}
          />
        </Himoya>

        <p className="text-matn-past px-1 text-xs leading-relaxed">
          🔒 {t("signal.himoya_izoh")}
        </p>

        {/* TP1 olingan: ikki xil odam, ikki xil xabar.
            Kirgan odamga — ko'rsatma (Stopni ko'taring).
            Kirmagan odamga — to'xtatuvchi yozuv. */}
        {signal.tp1Reached && (
          <Card variant="urgu">
            <CardTitle>🛡 {t("signal.breakeven_sarlavha")}</CardTitle>
            <p className="mt-2 text-sm leading-relaxed">{t("signal.breakeven_izoh")}</p>
            <p className="text-matn-past mt-3 text-xs uppercase">
              {t("signal.yangi_stop")}
            </p>
            <p className="raqam text-sarlavha text-lg font-bold">{narx(signal.entry)}</p>
          </Card>
        )}

        {!yangiKirish && !pozitsiya && (
          <div className="border-past/60 bg-past/10 rounded-kartochka border p-4">
            <p className="text-past text-sm font-semibold">⛔ {t("signal.faol_emas")}</p>
            <p className="text-matn-past mt-1 text-sm leading-relaxed">
              {t("signal.faol_emas_izoh")}
            </p>
          </div>
        )}

        {/* Kech kirish: narx kirish nuqtasidan uzoqlashgan bo'lsa,
            HALI KIRMAGAN odamga xavf kattalashgani aytiladi. */}
        {yangiKirish && !pozitsiya && (
          <KirishOgohlantirish
            juftlik={birjaJuftligi(signal.symbol, kotirovka())}
            kirish={signal.entry}
            chegara={kechKirishChegarasi()}
            matnlar={{
              sarlavha: t("signal.kech_ogoh"),
              izoh: t("signal.kech_ogoh_izoh"),
              masofa: t("signal.kech_masofa"),
            }}
          />
        )}

        {/* BALANS BIRINCHI. Balanssiz tizim hech narsa taklif qila
            olmaydi va foydalanuvchi "qancha olay?" degan savolga javob
            topmaydi — chalkashlik aynan shu yerdan boshlanardi. */}
        {foydalanuvchi && yangiKirish && balans === null && (
          <Card variant="urgu">
            <CardTitle>💰 {t("portfel.balans_kerak")}</CardTitle>
            <CardHint>{t("portfel.balans_kerak_izoh")}</CardHint>
            <div className="mt-3">
              <Button href="/portfel">{t("portfel.balans_yangi")}</Button>
            </div>
          </Card>
        )}

        {taklif && (
          <Card>
            <CardTitle>🧮 {t("signal.taklif_sarlavha")}</CardTitle>
            <p className="raqam text-sarlavha mt-1 text-3xl font-bold">
              ${pul(taklif.hajm)}
            </p>
            <p className="text-matn-past raqam mt-1 text-sm">
              📉 {t("signal.taklif_xavf")}: −${pul(taklif.xavf)}
            </p>
            <CardHint className="mt-2">
              {t("signal.taklif_izoh").replace("{foiz}", taklif.kunlikXavfFoiz.toFixed(1))}
            </CardHint>
            {taklif.kesilgan && (
              <CardHint className="mt-1">ℹ️ {t("signal.taklif_kesilgan")}</CardHint>
            )}
          </Card>
        )}

        <div className="grid gap-5 sm:grid-cols-2">
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
              symbol={`BINANCE:${birjaJuftligi(signal.symbol, kotirovka())}`}
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
            kotirovka={kotirovka()}
            boshlangichSumma={taklif?.hajm ?? null}
            entry={signal.entry}
            stop={stop}
            tpNarxlari={signal.tplar}
            olinganTplar={[signal.tp1Reached, false]}
            matnlar={kalkulyatorMatnlari(t)}
          />
        </Himoya>

        {foydalanuvchi && (
          <Card>
            <CardTitle>🖐 {t("signal.kirdim_sarlavha")}</CardTitle>
            {pozitsiya ? (
              <p className="text-yaxshi mt-2 text-sm">
                ✅{" "}
                {t("signal.kirdim_bor").replace(
                  "{amount}",
                  pul(pozitsiya.amountUsd),
                )}
              </p>
            ) : !yangiKirish ? (
              /* Kirish yopilgan signalga "Men sotib oldim" yozib
                 bo'lmaydi: bu kech kirishni RASMIYLASHTIRIB berardi. */
              <CardHint>{t("signal.faol_emas_izoh")}</CardHint>
            ) : (
              <>
                <CardHint>{t("signal.kirdim_izoh")}</CardHint>

                {/* Kirish narxi KO'RSATILADI, lekin tahrirlanmaydi: u
                    signalning o'zidan olinadi. Tahrirlansa, foydalanuvchi
                    o'ziga qulay narx yozib, statistikada mavjud bo'lmagan
                    foyda ko'rsatardi. */}
                <p className="text-matn-past mt-3 text-xs uppercase">
                  {t("signal.kirdim_narx")}
                </p>
                <p className="raqam text-sarlavha font-semibold">{narx(signal.entry)}</p>

                <form action={kirdim} className="mt-3 flex flex-wrap items-end gap-2">
                  <input type="hidden" name="signal_id" value={signal.id} />
                  <label className="min-w-0 flex-1">
                    <span className="text-matn-past mb-1 block text-xs uppercase">
                      {t("signal.kirdim_haqiqiy")}
                    </span>
                    {/* Taklif OLDINDAN yoziladi, lekin qulflanmaydi: biz
                        taklif qilamiz, foydalanuvchi esa HAQIQATDA qancha
                        olganini yozadi. Haqiqiy hisob-kitob shundan chiqadi. */}
                    <input
                      name="summa"
                      inputMode="decimal"
                      required
                      defaultValue={taklif ? taklif.hajm.toFixed(2) : ""}
                      placeholder="100"
                      className="border-ramka-yumshoq rounded-tugma bg-fon raqam w-full border px-3 py-2 text-sm"
                    />
                  </label>
                  <Button type="submit">{t("signal.kirdim_tugma")}</Button>
                </form>
              </>
            )}
            {kirdiMi && !pozitsiya && (
              <p className="text-yaxshi mt-2 text-sm">✅ {t("signal.kirdim_ok")}</p>
            )}
            {xato && (
              <p className="border-past/60 text-past rounded-kichik mt-2 border px-3 py-2 text-sm">
                ⚠️ {xato}
              </p>
            )}
          </Card>
        )}

        <Card>
          <CardTitle>{t("signal.ball_sabab")}</CardTitle>
          <BallTafsiloti xom={signal.scoreBreakdown} bosh={t("umumiy.yoq")} />
        </Card>

        {/* "Men sotib oldim" — botdagi `sig:enter:` ning sayt tomoni.
            Usiz portfel sahifasi saytdan kirgan odam uchun HECH QACHON
            to'lmasdi: yozuv faqat botdan yaratilardi. */}
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
