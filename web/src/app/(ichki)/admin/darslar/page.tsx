import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { type Tarif, darslar } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { darsOchirish, darsSaqlash } from "../amallar";

export const dynamic = "force-dynamic";

const TARIFLAR: Tarif[] = ["lite", "pro", "premium"];

type Dars = ReturnType<typeof darslar>[number];

export default async function Darslar() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const royxat = darslar();

  return (
    <>
      <Sarlavha matn={`🎬 ${t("admin.darslar")}`} izoh={t("admin.dars_izoh")} />

      <div className="space-y-5">
        <p className="border-ortacha/60 text-ortacha rounded-kichik border px-3 py-2 text-sm">
          ℹ️ {t("admin.dars_video_izoh")}
        </p>

        <Card variant="urgu">
          <CardTitle>➕ {t("admin.yangi_dars")}</CardTitle>
          <DarsFormasi t={t} />
        </Card>

        {royxat.length === 0 ? (
          <Card>
            <CardHint>{t("admin.dars_yoq")}</CardHint>
          </Card>
        ) : (
          royxat.map((d) => (
            <Card key={d.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle>{d.title}</CardTitle>
                <span className="flex flex-wrap items-center gap-2">
                  <Badge tone={d.published ? "yaxshi" : "neytral"}>
                    {d.published ? t("admin.chop_etilgan") : "—"}
                  </Badge>
                  {!d.fileId && <Badge tone="past">{t("admin.video_yoq")}</Badge>}
                </span>
              </div>
              <DarsFormasi t={t} dars={d} />
            </Card>
          ))
        )}
      </div>
    </>
  );
}

function DarsFormasi({ t, dars }: { t: (k: string) => string; dars?: Dars }) {
  const id = dars ? String(dars.id) : "";
  const pre = (nom: string) => `${id || "yangi"}-${nom}`;

  return (
    <>
      <form action={darsSaqlash} className="mt-3 space-y-3">
        <input type="hidden" name="id" value={id} />

        <div>
          <label className="text-matn-past mb-1 block text-xs uppercase" htmlFor={pre("title")}>
            {t("admin.sarlavha")}
          </label>
          <input
            id={pre("title")}
            name="title"
            required
            defaultValue={dars?.title ?? ""}
            className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="text-matn-past mb-1 block text-xs uppercase" htmlFor={pre("desc")}>
            {t("admin.tavsif")}
          </label>
          <input
            id={pre("desc")}
            name="description"
            defaultValue={dars?.description ?? ""}
            className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
          />
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <span>
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("tier")}
            >
              {t("admin.min_tarif")}
            </label>
            <select
              id={pre("tier")}
              name="min_tier"
              defaultValue={dars?.minTier ?? "pro"}
              className="border-ramka-yumshoq rounded-tugma bg-fon border px-3 py-2 text-sm"
            >
              {TARIFLAR.map((x) => (
                <option key={x} value={x}>
                  {x}
                </option>
              ))}
            </select>
          </span>

          <span>
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("pos")}
            >
              {t("admin.tartib")}
            </label>
            <input
              id={pre("pos")}
              name="position"
              inputMode="numeric"
              defaultValue={String(dars?.position ?? 0)}
              className="border-ramka-yumshoq rounded-tugma bg-fon raqam w-20 border px-3 py-2 text-sm"
            />
          </span>

          <label className="flex items-center gap-2 pb-2 text-sm">
            <input
              type="checkbox"
              name="published"
              defaultChecked={dars?.published ?? true}
              className="accent-[var(--rang-ramka)]"
            />
            {t("admin.chop_etilgan")}
          </label>
        </div>

        <div>
          <label className="text-matn-past mb-1 block text-xs uppercase" htmlFor={pre("file")}>
            {t("admin.file_id")}
          </label>
          <input
            id={pre("file")}
            name="file_id"
            placeholder={dars?.fileId ?? ""}
            className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
          />
        </div>

        <button
          type="submit"
          className="bg-ramka rounded-tugma px-4 py-2 text-sm font-semibold text-[#0a2450] hover:brightness-110"
        >
          {t("admin.saqlash")}
        </button>
      </form>

      {dars && (
        <form action={darsOchirish} className="mt-2">
          <input type="hidden" name="id" value={dars.id} />
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
