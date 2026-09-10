import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { type Havola, IKONKALAR, barchaHavolalar } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { havolaOchirish, havolaSaqlash } from "../amallar";
import { Ikonka } from "@/components/ui/Ikonka";

export const dynamic = "force-dynamic";

export default async function Havolalar() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const royxat = barchaHavolalar();

  return (
    <>
      <Sarlavha
        matn={t("admin.havolalar")}
        izoh={t("admin.havola_izoh")}
        belgi="havolalar"
      />

      <div className="space-y-5">
        <Card variant="urgu">
          <CardTitle className="flex items-center gap-2">
            <Ikonka nom="qosh" />
            {t("admin.yangi_havola")}
          </CardTitle>
          <HavolaFormasi t={t} />
        </Card>

        {royxat.length === 0 ? (
          <Card>
            <CardHint>{t("admin.havola_yoq")}</CardHint>
          </Card>
        ) : (
          royxat.map((h) => (
            <Card key={h.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle>{h.title}</CardTitle>
                <Badge tone={h.active ? "yaxshi" : "neytral"}>
                  {h.active ? t("admin.havola_faol") : "—"}
                </Badge>
              </div>
              <CardHint className="break-all">{h.url}</CardHint>
              <HavolaFormasi t={t} havola={h} />
            </Card>
          ))
        )}
      </div>
    </>
  );
}

function HavolaFormasi({
  t,
  havola,
}: {
  t: (k: string) => string;
  havola?: Havola;
}) {
  const id = havola ? String(havola.id) : "";
  const pre = (nom: string) => `${id || "yangi"}-h-${nom}`;

  return (
    <>
      <form action={havolaSaqlash} className="mt-3 space-y-3">
        <input type="hidden" name="id" value={id} />

        <div className="flex flex-wrap gap-3">
          <span className="min-w-0 flex-1">
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("t")}
            >
              {t("admin.havola_nomi")}
            </label>
            <input
              id={pre("t")}
              name="title"
              required
              defaultValue={havola?.title ?? ""}
              className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
            />
          </span>
          <span>
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("i")}
            >
              {t("admin.havola_ikonka")}
            </label>
            <select
              id={pre("i")}
              name="icon"
              defaultValue={havola?.icon ?? "telegram"}
              className="border-ramka-yumshoq rounded-tugma bg-fon border px-3 py-2 text-sm"
            >
              {IKONKALAR.map((x) => (
                <option key={x} value={x}>
                  {x}
                </option>
              ))}
            </select>
          </span>
          <span>
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("p")}
            >
              {t("admin.tartib")}
            </label>
            <input
              id={pre("p")}
              name="position"
              inputMode="numeric"
              defaultValue={String(havola?.position ?? 0)}
              className="border-ramka-yumshoq rounded-tugma bg-fon raqam w-20 border px-3 py-2 text-sm"
            />
          </span>
        </div>

        <div>
          <label
            className="text-matn-past mb-1 block text-xs uppercase"
            htmlFor={pre("u")}
          >
            {t("admin.havola_url")}
          </label>
          <input
            id={pre("u")}
            name="url"
            required
            type="url"
            placeholder="https://t.me/..."
            defaultValue={havola?.url ?? ""}
            className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
          />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="active"
            defaultChecked={havola?.active ?? true}
            className="accent-[var(--rang-ramka)]"
          />
          {t("admin.havola_faol")}
        </label>

        <button
          type="submit"
          className="bg-ramka rounded-tugma px-4 py-2 text-sm font-semibold text-[#0a2450] hover:brightness-110"
        >
          {t("admin.saqlash")}
        </button>
      </form>

      {havola && (
        <form action={havolaOchirish} className="mt-2">
          <input type="hidden" name="id" value={havola.id} />
          <button
            type="submit"
            className="border-past/70 text-past rounded-tugma border px-3 py-1.5 text-xs"
          >
            {t("admin.ochirish")}
          </button>
        </form>
      )}
    </>
  );
}
