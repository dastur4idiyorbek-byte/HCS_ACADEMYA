import { Yangilanmoqda } from "@/components/Yangilanmoqda";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { kutilayotganTolovlar } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { radEt, tasdiqla } from "./amallar";

export const dynamic = "force-dynamic";

export default async function Admin() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const tolovlar = kutilayotganTolovlar(50);

  return (
    <>
      <Sarlavha
        matn={t("admin.sarlavha")}
        ong={tolovlar.length > 0 ? <Badge tone="ortacha">{tolovlar.length}</Badge> : undefined}
      />

      <div className="space-y-5">
        <Card variant="urgu">
          <CardTitle>{t("admin.tolovlar")}</CardTitle>
          {tolovlar.length === 0 ? (
            <CardHint>{t("admin.tolov_yoq")}</CardHint>
          ) : (
            <ul className="mt-3 space-y-3">
              {tolovlar.map((p) => (
                <li key={p.id} className="border-ramka-yumshoq rounded-kichik border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="min-w-0">
                      <span className="text-sarlavha block text-sm font-semibold">
                        {p.fullName ?? p.username ?? `ID ${p.telegramId}`}
                      </span>
                      <span className="text-matn-past raqam block text-xs">
                        {p.tier} · {p.period} · {p.amount.toLocaleString("en-US")} {p.currency}
                      </span>
                    </span>
                    <span className="text-matn-past raqam text-xs">{sana(p.createdAt)}</span>
                  </div>

                  {/* Chek RASMI shu yerda ko'rinadi. Avval "chek botda
                      ko'riladi" deb turardi va admin har bir to'lov uchun
                      Telegramga o'tishi kerak edi. */}
                  {p.receiptFileId ? (
                    <a
                      href={`/api/chek/${p.id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="border-ramka-yumshoq rounded-kichik mt-2 block overflow-hidden border"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`/api/chek/${p.id}`}
                        alt={t("admin.chek")}
                        className="max-h-72 w-full object-contain"
                      />
                    </a>
                  ) : (
                    <CardHint className="mt-2">📎 {t("admin.chek_yoq")}</CardHint>
                  )}

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <form action={tasdiqla}>
                      <input type="hidden" name="id" value={p.id} />
                      <button
                        type="submit"
                        className="bg-ramka rounded-tugma px-3 py-2 text-xs font-semibold text-[#0a2450] hover:brightness-110"
                      >
                        ✅ {t("admin.tasdiqla")}
                      </button>
                    </form>

                    <form action={radEt} className="flex flex-1 flex-wrap items-center gap-2">
                      <input type="hidden" name="id" value={p.id} />
                      <input
                        type="text"
                        name="sabab"
                        placeholder={t("admin.rad_et")}
                        className="border-ramka-yumshoq rounded-tugma bg-fon min-w-0 flex-1 border px-3 py-2 text-xs"
                      />
                      <button
                        type="submit"
                        className="border-past/70 text-past rounded-tugma border px-3 py-2 text-xs font-semibold"
                      >
                        ✕
                      </button>
                    </form>
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
