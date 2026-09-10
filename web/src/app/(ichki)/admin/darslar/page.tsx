import { VideoYuklash } from "@/components/VideoYuklash";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { type Tarif, darslar } from "@/lib/queries";
import { kirim } from "@/lib/session";

import { darsOchirish, darsSaqlash } from "../amallar";
import { Ikonka } from "@/components/ui/Ikonka";

export const dynamic = "force-dynamic";

const TARIFLAR: Tarif[] = ["lite", "pro", "premium"];

type Dars = ReturnType<typeof darslar>[number];

export default async function Darslar() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const royxat = darslar();

  return (
    <>
      <Sarlavha matn={t("admin.darslar")} izoh={t("admin.dars_izoh")} />

      <div className="space-y-5">
        <p className="border-ortacha/60 text-ortacha rounded-kichik border px-3 py-2 text-sm">
          ℹ️ {t("admin.dars_video_izoh")}
        </p>

        {/* IKKI ALOHIDA FORMA, bitta "tur" tanlovi emas. Video
            formasida file_id kerak, maqolada esa matn — bitta
            formaga qo'shilsa, yarim maydon doim ortiqcha turardi va
            "buni to'ldirish kerakmi?" degan savol tug'ilardi. */}
        <Card variant="urgu">
          <CardTitle className="flex items-center gap-2">
            <Ikonka nom="qosh" />
            {t("admin.yangi_dars")}
          </CardTitle>
          <DarsFormasi t={t} turi="video" />
        </Card>

        <Card variant="urgu">
          <CardTitle className="flex items-center gap-2">
            <Ikonka nom="qosh" />
            {t("admin.yangi_maqola")}
          </CardTitle>
          <CardHint className="mt-1">{t("admin.maqola_izoh")}</CardHint>
          <DarsFormasi t={t} turi="maqola" />
        </Card>

        {royxat.length === 0 ? (
          <Card>
            <CardHint>{t("admin.dars_yoq")}</CardHint>
          </Card>
        ) : (
          royxat.map((d) => (
            <Card key={d.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="flex items-center gap-2">
                  <Ikonka nom={d.kind === "maqola" ? "maqolalar" : "video"} />
                  {d.title}
                </CardTitle>
                <span className="flex flex-wrap items-center gap-2">
                  <Badge tone={d.published ? "yaxshi" : "neytral"}>
                    {d.published ? t("admin.chop_etilgan") : "—"}
                  </Badge>
                  {d.kind === "maqola" ? null : d.videoPath ? (
                    <Badge tone="yaxshi">{t("admin.video_saytda")}</Badge>
                  ) : d.fileId ? (
                    <Badge tone="neytral">{t("admin.video_botda")}</Badge>
                  ) : (
                    <Badge tone="past">{t("admin.video_yoq")}</Badge>
                  )}
                </span>
              </div>

              {/* Video FAYLI shu yerdan yuklanadi — dars formasidan
                  alohida. Sabab: forma serverga bir zumda yuboriladi,
                  fayl esa daqiqalab yuklanadi. Bittaga qo'shilsa,
                  sarlavhani tuzatish uchun ham videoni kutish kerak
                  bo'lardi. */}
              {d.kind !== "maqola" && (
                <VideoYuklash
                  darsId={d.id}
                  bormi={Boolean(d.videoPath)}
                  matnlar={{
                    yukla: t("admin.video_yukla"),
                    almashtir: t("admin.video_almashtir"),
                    yuklanmoqda: t("admin.video_yuklanmoqda"),
                    tarmoq_xatosi: t("admin.video_tarmoq_xatosi"),
                  }}
                />
              )}

              <DarsFormasi
                t={t}
                dars={d}
                turi={d.kind === "maqola" ? "maqola" : "video"}
              />
            </Card>
          ))
        )}
      </div>
    </>
  );
}

function DarsFormasi({
  t,
  dars,
  turi,
}: {
  t: (k: string) => string;
  dars?: Dars;
  turi: "video" | "maqola";
}) {
  const id = dars ? String(dars.id) : "";
  // Yangi maqola va yangi dars formalari BIR SAHIFADA turadi —
  // prefiks turni ham o'z ichiga oladi, aks holda ikkala formada
  // bir xil `id` chiqib, yorliq bosilganda noto'g'ri maydonga
  // o'tardi.
  const pre = (nom: string) => `${id || `yangi-${turi}`}-${nom}`;
  const maqola = turi === "maqola";

  return (
    <>
      <form action={darsSaqlash} className="mt-3 space-y-3">
        <input type="hidden" name="id" value={id} />
        <input type="hidden" name="kind" value={turi} />

        <div>
          <label
            className="text-matn-past mb-1 block text-xs uppercase"
            htmlFor={pre("title")}
          >
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
          <label
            className="text-matn-past mb-1 block text-xs uppercase"
            htmlFor={pre("desc")}
          >
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

        {/* Toifa va o'qish vaqti — IKKALA turga ham. Video uchun
            "davomiylik", maqola uchun "o'qish vaqti": bir xil maydon,
            chunki ikkalasi ham "buni ko'rishga qancha vaqt ketadi"
            degan savolga javob. */}
        <div className="flex flex-wrap items-end gap-3">
          <span className="min-w-[12rem] flex-1">
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("toifa")}
            >
              {t("admin.toifa")}
            </label>
            <input
              id={pre("toifa")}
              name="toifa"
              defaultValue={dars?.toifa ?? ""}
              placeholder={t("admin.toifa_misol")}
              className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
            />
          </span>

          <span>
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("vaqt")}
            >
              {maqola ? t("admin.oqish_vaqti") : t("admin.davomiylik")}
            </label>
            <input
              id={pre("vaqt")}
              name="davomiylik"
              inputMode="numeric"
              defaultValue={
                dars?.davomiylik ? String(Math.round(dars.davomiylik / 60)) : ""
              }
              placeholder={t("admin.daqiqa")}
              className="border-ramka-yumshoq rounded-tugma bg-fon raqam w-24 border px-3 py-2 text-sm"
            />
          </span>
        </div>

        {maqola ? (
          <div>
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("matn")}
            >
              {t("admin.maqola_matni")}
            </label>
            {/* Oddiy matn maydoni — HTML muharriri emas. Maqola
                sahifasi matnni `whitespace-pre-wrap` bilan chizadi,
                ya'ni qator va bo'sh qatorlar saqlanadi. HTML qabul
                qilinsa, admin panelidan sahifaga kod tushish yo'li
                ochilardi. */}
            <textarea
              id={pre("matn")}
              name="matn"
              rows={10}
              required
              defaultValue={dars?.matn ?? ""}
              className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm leading-relaxed"
            />
          </div>
        ) : (
          <div>
            <label
              className="text-matn-past mb-1 block text-xs uppercase"
              htmlFor={pre("file")}
            >
              {t("admin.file_id")}
            </label>
            <input
              id={pre("file")}
              name="file_id"
              placeholder={dars?.fileId ?? ""}
              className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
            />
          </div>
        )}

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
