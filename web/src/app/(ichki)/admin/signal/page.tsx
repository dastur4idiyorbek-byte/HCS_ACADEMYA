import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { narx, sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { signalOgohlantirishlari, signalOl, tarqatilmaganSignallar } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { signalBer } from "../amallar";

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
        tp2: yaratilgan.tp2,
        note: null,
      })
    : [];

  const kutayotganlar = tarqatilmaganSignallar();

  return (
    <>
      <Sarlavha matn={`📈 ${t("admin.signal")}`} izoh={t("admin.signal_izoh")} />

      <div className="space-y-5">
        {yaratilgan && (
          <Card variant="urgu">
            <CardTitle>✅ {t("admin.yozildi")}</CardTitle>
            <CardHint>
              {yaratilgan.symbol} · {t("signal.entry")} {narx(yaratilgan.entry)}
            </CardHint>

            {ogohlantirishlar.length > 0 && (
              <div className="border-ortacha/60 rounded-kichik mt-3 border p-3">
                <p className="text-ortacha text-sm font-semibold">
                  ⚠️ {t("admin.ogohlantirishlar")}
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
              <label className="text-matn-past mb-1 block text-xs uppercase" htmlFor="symbol">
                {t("admin.symbol")}
              </label>
              <input
                id="symbol"
                name="symbol"
                required
                placeholder="BTCUSDT"
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
              <label className="text-matn-past mb-1 block text-xs uppercase" htmlFor="note">
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
            {kutayotganlar.length > 0 && <Badge tone="ortacha">{kutayotganlar.length}</Badge>}
          </div>
          {kutayotganlar.length === 0 ? (
            <CardHint>{t("admin.kutilmoqda_yoq")}</CardHint>
          ) : (
            <ul className="mt-3 space-y-1.5">
              {kutayotganlar.map((s) => (
                <li key={s.id} className="flex justify-between gap-3 text-sm">
                  <span className="text-sarlavha font-medium">{s.symbol}</span>
                  <span className="text-matn-past raqam text-xs">{sana(s.createdAt)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
