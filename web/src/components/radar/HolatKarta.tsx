import type { ReactNode } from "react";

import { Card } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { cn } from "@/lib/cn";
import type { RadarHolati } from "@/lib/radar-baza";
import { type Sessiya, mintaqaCheklanganmi, shablon } from "@/lib/radar";

import { type Tarjimon, tYoki, vaqtMatni } from "./matn";

/** Ishchi shu vaqt ichida yurak urishi yozmagan bo'lsa — "javob bermayapti". */
const TIRIK_DAQIQA = 3;

/** Radar holati: ishchi tirikmi, oxirgi rasmiy sessiya, keyingi
 *  sessiyalar, manbalar va "Hozir tekshir" tugmasi.
 *
 * Sayt va bot — ikki alohida jarayon, ular faqat baza orqali
 * gaplashadi. Shuning uchun "ishchi ishlayaptimi" degan savolga yagona
 * javob — `radar_holati.ishchi_tirik` (yurak urishi).
 *
 * 451 ALOHIDA va OCHIQ ko'rsatiladi: bu vaqtincha nosozlik emas —
 * Binance shu server mintaqasini cheklagan va bu serverdan radar
 * umuman ishlay olmaydi. Buni "xato" degan kichik yozuv ostida
 * yashirish admin vaqtini kunlab yeyishi mumkin edi.
 */
export function HolatKarta({
  holati,
  hozir,
  oxirgi,
  songgi,
  keyingi,
  zona,
  t,
  tugma,
}: {
  holati: RadarHolati;
  hozir: Date;
  /** Oxirgi tugagan rasmiy (B) sessiya */
  oxirgi: Sessiya | null;
  /** Eng so'nggi sessiya — har qanday tur va holatda */
  songgi: Sessiya | null;
  keyingi: { kashfiyot: Date; tasdiq: Date };
  zona: string;
  t: Tarjimon;
  /** "Hozir tekshir" — mijoz komponenti, sahifadan uzatiladi */
  tugma: ReactNode;
}) {
  const tirik =
    holati.ishchiTirik !== null &&
    hozir.getTime() - holati.ishchiTirik.getTime() <= TIRIK_DAQIQA * 60_000;
  const manbalar = (songgi?.manbalar.length ? songgi : oxirgi)?.manbalar ?? [];
  const taqiq = mintaqaCheklanganmi(manbalar);

  return (
    <Card className="mb-5" id="holat">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-2 text-sm">
          <p className="flex items-center gap-2 font-semibold">
            <span className={tirik ? "text-yaxshi" : "text-past"} aria-hidden>
              ●
            </span>
            {tirik ? t("radar.ishchi_tirik") : t("radar.ishchi_olik")}
          </p>
          {!tirik ? (
            <p className="text-matn-past text-xs">
              {holati.ishchiTirik
                ? shablon(t("radar.ishchi_olik_izoh"), { v: vaqtMatni(t, holati.ishchiTirik, zona) })
                : t("radar.ishchi_hech")}
            </p>
          ) : null}

          <div>
            <p className="text-matn-past text-xs">{t("radar.oxirgi_sessiya")}</p>
            <p className="text-matn raqam">
              {oxirgi ? vaqtMatni(t, oxirgi.boshlandi, zona) : t("radar.sessiya_hali_yoq")}
            </p>
            {oxirgi ? (
              <p className="text-matn-past raqam mt-0.5 text-xs">
                {t("radar.sanoq_universum")}: {oxirgi.universum} · {t("radar.sanoq_darvoza")}:{" "}
                {oxirgi.darvozadan} · {t("radar.sanoq_elak")}: {oxirgi.elakdan} ·{" "}
                {t("radar.sanoq_nomzod")}: <span className="text-matn">{oxirgi.nomzod}</span>
              </p>
            ) : null}
          </div>

          {songgi?.holat === "yurmoqda" ? (
            <p className="text-ortacha text-xs">
              {shablon(t("radar.sessiya_yurmoqda"), { v: vaqtMatni(t, songgi.boshlandi, zona) })}
            </p>
          ) : songgi?.holat === "xato" ? (
            <p className="text-past text-xs">
              {t("radar.sessiya_xato")}
              {songgi.izoh ? `: ${songgi.izoh}` : "."}
            </p>
          ) : null}

          <div className="grid gap-2 sm:grid-cols-2">
            <div>
              <p className="text-matn-past text-xs">{t("radar.keyingi_a")}</p>
              <p className="text-matn raqam">{vaqtMatni(t, keyingi.kashfiyot, zona)}</p>
            </div>
            <div>
              <p className="text-matn-past text-xs">{t("radar.keyingi_b")}</p>
              <p className="text-sarlavha raqam font-semibold">
                {vaqtMatni(t, keyingi.tasdiq, zona)}
              </p>
            </div>
          </div>
          <p className="text-matn-past text-[11px]">{shablon(t("radar.vaqt_zonasi"), { z: zona })}</p>
        </div>

        <div className="flex flex-col items-start gap-2">
          {tugma}
          {holati.sorov ? (
            <p className="text-ortacha max-w-xs text-xs">{t("radar.soraldi_kutilmoqda")}</p>
          ) : null}
        </div>
      </div>

      {taqiq ? (
        <div className="border-past bg-fon text-past rounded-kichik mt-4 border p-3 text-sm">
          <p className="flex items-center gap-2 font-semibold">
            <Ikonka nom="ogohlantirish" className="h-4 w-4" />
            {t("radar.taqiq_sarlavha")}
          </p>
          <p className="text-matn mt-1 text-xs leading-relaxed">{t("radar.taqiq_matn")}</p>
        </div>
      ) : null}

      {manbalar.length > 0 ? (
        <div className="mt-4">
          <p className="text-matn-past mb-1.5 text-xs">{t("radar.manbalar")}</p>
          <ul className="flex flex-wrap gap-1.5">
            {manbalar.map((m) => (
              <li
                key={m.nom}
                title={m.izoh || undefined}
                className={cn(
                  "bg-fon inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs",
                  m.holat === "ok" ? "border-yaxshi/50 text-matn" : "border-past/70 text-past",
                )}
              >
                <Ikonka
                  nom={m.holat === "ok" ? "faol" : "bekor"}
                  className={cn("h-3 w-3", m.holat === "ok" ? "text-yaxshi" : "text-past")}
                />
                {tYoki(t, `radar.manba.${m.nom}`, m.nom)}
                <span className="sr-only">
                  {m.holat === "ok" ? t("radar.manba_ok") : t("radar.manba_xato")}
                </span>
                {m.holat !== "ok" && m.kod !== null ? (
                  <span className="raqam">({m.kod})</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {holati.oxirgiXato ? (
        <p className="text-past mt-3 text-xs break-words">
          <strong>{t("radar.oxirgi_xato")}:</strong> {holati.oxirgiXato}
        </p>
      ) : null}
    </Card>
  );
}
