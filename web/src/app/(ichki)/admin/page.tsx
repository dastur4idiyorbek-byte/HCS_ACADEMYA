import { SalomatlikShkalasi, SalomatlikYoq } from "@/components/Salomatlik";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { salomatlikBandlari, smcSozlamalari } from "@/lib/config";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { kutilayotganTolovlar, salomatlikOxirgi, salomatlikTarixi } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { radEt, tasdiqla } from "./amallar";

export const dynamic = "force-dynamic";

export default async function Admin() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const tolovlar = kutilayotganTolovlar(50);
  const salomatlik = salomatlikOxirgi();
  const tarix = salomatlikTarixi(8);
  const smc = smcSozlamalari();
  const holat = (yoq: boolean) => t(yoq ? "admin.yoqilgan" : "admin.ochirilgan");
  const bandlar = salomatlikBandlari();

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

        <Card>
          <CardTitle>{t("admin.salomatlik")}</CardTitle>
          <div className="mt-3">
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

          {tarix.length > 1 && (
            <>
              <p className="text-matn-past mt-4 text-xs uppercase">{t("admin.tarix")}</p>
              <ul className="mt-2 space-y-1">
                {tarix.map((h, i) => (
                  <li key={i} className="flex justify-between gap-3 text-xs">
                    <span className="text-matn-past raqam">{sana(h.createdAt)}</span>
                    <span className="raqam font-semibold">{h.value.toFixed(1)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>

        {/* CryptoSpot3% qatlami — FAQAT KO'RSATISH.
            Tahrirlash tugmasini qo'yib, aslida saqlamaslik eng yomon
            variant bo'lardi: admin o'zgartirdim deb o'ylaydi, tizim
            esa eski qiymat bilan ishlashda davom etadi. */}
        <Card>
          <CardTitle>{t("admin.smc")}</CardTitle>
          <CardHint>{t("admin.smc_izoh")}</CardHint>

          <dl className="mt-3 space-y-2 text-sm">
            <SozlamaQatori
              nom={t("admin.smc_struktura_majburiy")}
              qiymat={holat(smc.strukturaMajburiy)}
            />
            <SozlamaQatori nom={t("admin.smc_yalash")} qiymat={holat(smc.yalashYoqilgan)} />
            <SozlamaQatori
              nom={t("admin.smc_yalash_chuqurlik")}
              qiymat={`${smc.yalashChuqurligi}%`}
            />
            <SozlamaQatori nom={t("admin.smc_yalash_oyna")} qiymat={String(smc.yalashOynasi)} />
            <SozlamaQatori nom={t("admin.smc_qaytish")} qiymat={String(smc.qaytishShamlari)} />
            <SozlamaQatori
              nom={t("admin.smc_sessiya")}
              qiymat={
                smc.sessiyaYoqilgan
                  ? `${String(smc.sessiyaBoshi).padStart(2, "0")}:00-` +
                    `${String(smc.sessiyaOxiri).padStart(2, "0")}:00 UTC`
                  : holat(false)
              }
            />
          </dl>

          <p className="text-matn-past mt-4 text-xs uppercase">{t("admin.smc_kotarish")}</p>
          <dl className="mt-2 space-y-2 text-sm">
            <SozlamaQatori
              nom="🔵 Struktura → trend"
              qiymat={`×${smc.kotarishStruktura}`}
            />
            <SozlamaQatori
              nom="🧲 Sweep + daraja → S/R"
              qiymat={`×${smc.kotarishZona}`}
            />
            <SozlamaQatori nom="⏰ Kill Zone bonusi" qiymat={`+${smc.bonusSessiya}`} />
          </dl>
          <p className="text-matn-past mt-3 text-xs leading-relaxed">
            {t("admin.smc_bonus_izoh")}
          </p>
        </Card>
      </div>
    </>
  );
}

function SozlamaQatori({ nom, qiymat }: { nom: string; qiymat: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-matn-past">{nom}</dt>
      <dd className="raqam text-sarlavha font-semibold">{qiymat}</dd>
    </div>
  );
}
