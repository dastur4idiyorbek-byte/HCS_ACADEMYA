import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { foiz, holatNomi, narx, sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import {
  adminSignallar,
  signalOgohlantirishlari,
  signalOl,
  tarqatilmaganSignallar,
} from "@/lib/queries";
import { kirim } from "@/lib/session";

import { signalBer, signalOchirish } from "../amallar";

import { SignalRasmlari } from "./rasmlar";
import { Ikonka } from "@/components/ui/Ikonka";

export const dynamic = "force-dynamic";

const MAYDONLAR = [
  { nom: "entry", kalit: "admin.kirish_narx" },
  { nom: "stop", kalit: "admin.stop_narx" },
  { nom: "tp1", kalit: "admin.tp1_narx" },
  { nom: "tp2", kalit: "admin.tp2_narx" },
] as const;

export default async function YangiSignal({
  searchParams,
}: {
  searchParams: Promise<{ ok?: string; xato?: string }>;
}) {
  const { til } = await kirim();
  const t = tarjimon(til);
  const { ok, xato } = await searchParams;

  // Ogohlantirishlar SAQLANGAN signaldan qayta hisoblanadi — ekrandagi
  // matn har doim bazadagi holatga tegishli bo'lsin.
  const yaratilgan = ok ? signalOl(Number(ok)) : null;
  const ogohlantirishlar = yaratilgan
    ? signalOgohlantirishlari({
        symbol: yaratilgan.symbol,
        entry: yaratilgan.entry,
        stop: yaratilgan.stop,
        tp1: yaratilgan.tp1,
        // Qo'lda kiritish shakli ikkita TP so'raydi, lekin saqlangan
        // signalda TP soni qat'iy emas — bittasi ham bo'lishi mumkin.
        tp2: yaratilgan.tp2 ?? yaratilgan.tp1,
        note: null,
      })
    : [];

  const kutayotganlar = tarqatilmaganSignallar();
  const barchasi = adminSignallar();

  return (
    <>
      <Sarlavha matn={t("admin.signal")} izoh={t("admin.signal_izoh")} />

      <div className="space-y-5">
        {yaratilgan && (
          <Card variant="urgu">
            <CardTitle className="flex items-center gap-2">
              <Ikonka nom="faol" />
              {t("admin.yozildi")}
            </CardTitle>
            <CardHint>
              {yaratilgan.symbol} · {t("signal.entry")} {narx(yaratilgan.entry)}
            </CardHint>

            {ogohlantirishlar.length > 0 && (
              <div className="border-ortacha/60 rounded-kichik mt-3 border p-3">
                <p className="text-ortacha text-sm font-semibold">
                  <Ikonka
                    nom="ogohlantirish"
                    className="inline h-4 w-4 align-[-3px]"
                  />{" "}
                  {t("admin.ogohlantirishlar")}
                </p>
                <ul className="text-ortacha mt-2 space-y-1 text-sm">
                  {ogohlantirishlar.map((o) => (
                    <li key={o}>• {o}</li>
                  ))}
                </ul>
                <CardHint className="mt-2">{t("admin.ogoh_izoh")}</CardHint>
              </div>
            )}
          </Card>
        )}

        {xato && (
          <p className="border-past/60 text-past rounded-kichik border px-3 py-2 text-sm">
            {xato}
          </p>
        )}

        <Card>
          <CardTitle>{t("admin.signal")}</CardTitle>
          <form action={signalBer} className="mt-4 space-y-3">
            <div>
              <label
                className="text-matn-past mb-1 block text-xs uppercase"
                htmlFor="symbol"
              >
                {t("admin.symbol")}
              </label>
              <input
                id="symbol"
                name="symbol"
                required
                placeholder="BTC"
                className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm uppercase sm:w-56"
              />
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {MAYDONLAR.map((m) => (
                <div key={m.nom}>
                  <label
                    className="text-matn-past mb-1 block text-xs uppercase"
                    htmlFor={m.nom}
                  >
                    {t(m.kalit)}
                  </label>
                  <input
                    id={m.nom}
                    name={m.nom}
                    required
                    inputMode="decimal"
                    className="border-ramka-yumshoq rounded-tugma bg-fon raqam w-full border px-3 py-2 text-sm"
                  />
                </div>
              ))}
            </div>

            <div>
              <label
                className="text-matn-past mb-1 block text-xs uppercase"
                htmlFor="note"
              >
                {t("admin.signal_izoh_maydoni")}
              </label>
              <input
                id="note"
                name="note"
                className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              className="bg-ramka rounded-tugma px-4 py-2 text-sm font-semibold text-[#0a2450] hover:brightness-110"
            >
              {t("admin.yuborish")}
            </button>
          </form>

          <CardHint className="mt-4">ℹ️ {t("admin.signal_nega_bot")}</CardHint>
        </Card>

        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>{t("admin.kutilmoqda")}</CardTitle>
            {kutayotganlar.length > 0 && (
              <Badge tone="ortacha">{kutayotganlar.length}</Badge>
            )}
          </div>
          {kutayotganlar.length === 0 ? (
            <CardHint>{t("admin.kutilmoqda_yoq")}</CardHint>
          ) : (
            <ul className="mt-3 space-y-1.5">
              {kutayotganlar.map((s) => (
                <li key={s.id} className="flex justify-between gap-3 text-sm">
                  <span className="text-sarlavha font-medium">{s.symbol}</span>
                  <span className="text-matn-past raqam text-xs">
                    {sana(s.createdAt)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Barcha signallar — o'chirish uchun. Sinov paytida yaratilgan
            soxta signal statistikaga kiradi va uni buzadi: bitta
            "-94%" butun g'alaba foizini yaroqsiz qiladi. */}
        <Card>
          <CardTitle>{t("admin.signal_royxat")}</CardTitle>
          <CardHint>{t("admin.signal_royxat_izoh")}</CardHint>

          {barchasi.length === 0 ? (
            <CardHint className="mt-3">{t("admin.kutilmoqda_yoq")}</CardHint>
          ) : (
            <ul className="mt-3 space-y-2">
              {barchasi.map((s) => (
                <li
                  key={s.id}
                  className="border-ramka-yumshoq rounded-kichik flex flex-wrap items-center justify-between gap-2 border p-2.5"
                >
                  <span className="min-w-0">
                    <span className="text-sarlavha font-medium">
                      {s.symbol}
                    </span>{" "}
                    <span className="text-matn-past raqam text-xs">
                      {holatNomi(s.status, til)} · {narx(s.entry)} ·{" "}
                      {sana(s.createdAt)}
                      {s.resultPct !== null && ` · ${foiz(s.resultPct)}`}
                    </span>
                  </span>
                  <form action={signalOchirish}>
                    <input type="hidden" name="id" value={s.id} />
                    <button
                      type="submit"
                      className="border-past/70 text-past rounded-tugma border px-3 py-1.5 text-xs"
                    >
                      {t("admin.ochirish")}
                    </button>
                  </form>

                  {/* Grafik rasmlari (4-prompt, 4-qism). Ochiq
                      turadi, yig'ilmaydi: admin signal yopilganda
                      natija rasmini qo'shishi kerak va yashirin
                      bo'lsa buni unutish oson bo'lardi. */}
                  <div className="w-full">
                    <SignalRasmlari
                      signalId={s.id}
                      til={til}
                      kirishRasmi={s.entryChartImage}
                      natijaRasmi={s.resultChartImage}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
