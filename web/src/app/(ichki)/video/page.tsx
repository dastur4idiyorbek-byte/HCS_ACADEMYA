import { VideoPleyer } from "@/components/VideoPleyer";
import { Qulf } from "@/components/ui/Qulf";
import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { botHavolasi, env } from "@/lib/env";
import { tarjimon } from "@/lib/i18n";
import { kontent, tarifQamraydi } from "@/lib/queries";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function Video() {
  const { til, tarif, foydalanuvchi } = await kirim();
  const t = tarjimon(til);
  const botUsername = env().botUsername;

  if (!tarifQamraydi(tarif, "pro")) {
    return (
      <>
        <Sarlavha matn={t("kontent.video")} />
        <Qulf til={til} kerakliTarif="pro" botUsername={botUsername} />
      </>
    );
  }

  // Foydalanuvchi tarifi qamrab oladigan darslar. Bu yerda ham filtr
  // SERVERDA: qulflangan darsning nomi ham sotiladigan qiymat.
  const darslar = kontent().filter((k) => k.kind === "video" && tarifQamraydi(tarif, k.minTier));

  return (
    <>
      <Sarlavha matn={t("kontent.video")} izoh={t("kontent.botda_izoh")} />

      {darslar.length === 0 ? (
        <Card>
          <p className="text-matn-past text-sm">{t("kontent.yoq")}</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {darslar.map((d) => (
            <Card key={d.id}>
              <CardTitle>
                🎬 {d.title}
              </CardTitle>
              {d.description && <CardHint>{d.description}</CardHint>}

              {/* Video saytga yuklangan bo'lsa — shu yerda o'ynaydi.
                  Yuklanmagan darslar uchun botga havola qoladi: eski
                  darslar faqat Telegramda, ular ko'rinmay qolmasin. */}
              {d.videoPath ? (
                <div className="mt-3">
                  <VideoPleyer
                    darsId={d.id}
                    belgi={`HCS · ${foydalanuvchi?.telegramId ?? "—"}`}
                  />
                  <p className="text-matn-past mt-2 text-xs leading-relaxed">
                    🔒 {t("kontent.himoya_izoh")}
                  </p>
                </div>
              ) : (
                <div className="mt-3">
                  <Button href={botHavolasi(botUsername, "start")} variant="ikkilamchi">
                    {t("kontent.botda_koring")}
                  </Button>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
