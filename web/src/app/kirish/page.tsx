import { redirect } from "next/navigation";

import { TelegramKirish } from "@/components/TelegramKirish";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Logo } from "@/components/ui/Logo";
import { EnvError, env } from "@/lib/env";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

export default async function Kirish({
  searchParams,
}: {
  searchParams: Promise<{ xato?: string }>;
}) {
  const { kirgan, til } = await kirim();
  if (kirgan) redirect("/bosh");

  const t = tarjimon(til);
  const { xato } = await searchParams;

  let botUsername: string | null = null;
  let sozlamaXatosi: string | null = null;
  try {
    botUsername = env().botUsername;
  } catch (e) {
    // Sozlama yetishmasa AYNIQSA shu sahifada aniq aytish kerak: aks holda
    // "tugma chiqmayapti" deb soatlab qidiriladi.
    sozlamaXatosi = e instanceof EnvError ? e.message : String(e);
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center px-4 py-10">
      <div className="mb-8 flex justify-center">
        <Logo size={64} />
      </div>

      <Card variant="urgu">
        <CardTitle>{t("kirish.sarlavha")}</CardTitle>
        <CardHint>{t("kirish.izoh")}</CardHint>

        {xato && (
          <p className="border-past/60 text-past rounded-kichik mt-4 border px-3 py-2 text-sm">
            {t("kirish.xato")}
          </p>
        )}

        <div className="mt-5 flex justify-center">
          {botUsername ? (
            <TelegramKirish botUsername={botUsername} />
          ) : (
            <p className="text-past text-sm">{sozlamaXatosi}</p>
          )}
        </div>

        <div className="mt-6 space-y-2 border-t border-white/10 pt-4">
          <p className="text-matn-past text-xs leading-relaxed">🔐 {t("kirish.xavfsizlik")}</p>
          <p className="text-matn-past text-xs leading-relaxed">⏳ {t("kirish.muddat")}</p>
        </div>
      </Card>
    </main>
  );
}
