import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { type Narx, narxlar } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { narxSaqla } from "../amallar";

export const dynamic = "force-dynamic";

/** Qaysi tarif+muddat+valyuta juftliklari bo'lishi kerak.
 *
 * Bazada hali yo'q qatorlar ham ko'rsatiladi (bo'sh forma bilan) —
 * aks holda admin "USDT narxini qayerdan qo'shaman?" degan savolda
 * qolib ketardi. */
const TARIFLAR = ["lite", "pro", "premium"] as const;
const MUDDATLAR = ["daily", "monthly"] as const;
const VALYUTALAR = ["KGS", "USDT"] as const;

export default async function Narxlar() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const mavjud = narxlar();

  const top = (
    tier: string,
    period: string,
    currency: string,
  ): Narx | undefined =>
    mavjud.find(
      (n) => n.tier === tier && n.period === period && n.currency === currency,
    );

  return (
    <>
      <Sarlavha matn={`🏷 ${t("admin.narxlar")}`} izoh={t("admin.narx_izoh")} />

      <div className="space-y-5">
        {TARIFLAR.map((tier) => (
          <Card key={tier}>
            <CardTitle>{tier.toUpperCase()}</CardTitle>
            <div className="mt-3 space-y-3">
              {MUDDATLAR.flatMap((period) =>
                VALYUTALAR.map((currency) => {
                  const n = top(tier, period, currency);
                  return (
                    <form
                      key={`${period}-${currency}`}
                      action={narxSaqla}
                      className="border-ramka-yumshoq rounded-kichik border p-3"
                    >
                      <input type="hidden" name="tier" value={tier} />
                      <input type="hidden" name="period" value={period} />
                      <input type="hidden" name="currency" value={currency} />

                      <p className="text-matn-past mb-2 text-xs uppercase">
                        {period === "daily"
                          ? t("profil.kunlik")
                          : t("profil.oylik")}{" "}
                        · {currency}
                      </p>

                      <div className="flex flex-wrap items-center gap-2">
                        <label
                          className="sr-only"
                          htmlFor={`s-${tier}-${period}-${currency}`}
                        >
                          {t("admin.summa_kiriting")}
                        </label>
                        <input
                          id={`s-${tier}-${period}-${currency}`}
                          name="amount"
                          inputMode="decimal"
                          defaultValue={n ? String(n.amount) : ""}
                          placeholder={t("admin.summa_kiriting")}
                          className="border-ramka-yumshoq rounded-tugma bg-fon raqam w-32 border px-3 py-2 text-sm"
                        />
                        <input
                          name="payment_details"
                          defaultValue=""
                          placeholder={t("admin.rekvizit")}
                          className="border-ramka-yumshoq rounded-tugma bg-fon min-w-0 flex-1 border px-3 py-2 text-sm"
                        />
                        <button
                          type="submit"
                          className="bg-ramka rounded-tugma px-3 py-2 text-xs font-semibold text-[#0a2450] hover:brightness-110"
                        >
                          {t("admin.saqlash")}
                        </button>
                      </div>

                      {n?.paymentDetails && (
                        <p className="text-matn-past mt-2 text-xs">
                          {t("admin.rekvizit")}: {n.paymentDetails}
                        </p>
                      )}
                    </form>
                  );
                }),
              )}
            </div>
            <CardHint className="mt-3">{t("admin.rekvizit_izoh")}</CardHint>
          </Card>
        ))}
      </div>
    </>
  );
}
