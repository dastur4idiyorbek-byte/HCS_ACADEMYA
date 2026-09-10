"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { tarjimon } from "@/lib/i18n";

import { signalRasmiBiriktir } from "../amallar";
import { Ikonka } from "@/components/ui/Ikonka";

/** Signal grafigini yuklash — admin (4-prompt, 4-qism).
 *
 * IKKI QADAM, bosh sahifa posti bilan bir xil sabab: server amali
 * FormData ni butunlay xotiraga yig'adi va Next.js ning 1 MB
 * chegarasi skrinshotni to'sib qo'yardi. Rasm alohida yo'l bilan
 * diskka yoziladi, formaga faqat NOMI tushadi.
 */
export function SignalRasmlari({
  signalId,
  til,
  kirishRasmi,
  natijaRasmi,
}: {
  signalId: number;
  til: "uz" | "ru";
  kirishRasmi: string | null;
  natijaRasmi: string | null;
}) {
  const t = tarjimon(til);

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Maydon
        signalId={signalId}
        maydon="entry"
        nomi={t("admin.rasm_kirish")}
        joriy={kirishRasmi}
        t={t}
      />
      <Maydon
        signalId={signalId}
        maydon="natija"
        nomi={t("admin.rasm_natija")}
        joriy={natijaRasmi}
        t={t}
      />
    </div>
  );
}

function Maydon({
  signalId,
  maydon,
  nomi,
  joriy,
  t,
}: {
  signalId: number;
  maydon: "entry" | "natija";
  nomi: string;
  joriy: string | null;
  t: (k: string) => string;
}) {
  const [nom, setNom] = useState<string | null>(null);
  const [holat, setHolat] = useState<string | null>(null);
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const faylRef = useRef<HTMLInputElement>(null);

  async function yukla(): Promise<void> {
    const fayl = faylRef.current?.files?.[0];
    if (!fayl) return;

    setYuklanmoqda(true);
    setHolat(null);
    try {
      const javob = await fetch(
        `/api/admin/signal-media?nom=${encodeURIComponent(fayl.name)}`,
        { method: "POST", body: fayl },
      );
      const natija = (await javob.json()) as { nom?: string; xato?: string };
      if (!javob.ok || !natija.nom) {
        setHolat(natija.xato ?? t("admin.rasm_yuklanmadi"));
        return;
      }
      setNom(natija.nom);
      setHolat(t("admin.rasm_yuklandi"));
    } catch {
      setHolat(t("admin.rasm_yuklanmadi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  return (
    <div className="border-ramka-yumshoq rounded-kartochka border p-3">
      <p className="text-matn-past mb-2 text-xs uppercase">{nomi}</p>

      {joriy && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={`/api/signal-media/${joriy}`}
          alt={nomi}
          className="rounded-tugma mb-2 max-h-40 w-full object-contain"
        />
      )}

      <input
        ref={faylRef}
        type="file"
        accept="image/*"
        onChange={() => {
          setNom(null);
          setHolat(null);
        }}
        className="text-matn-past w-full text-sm"
      />

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="ikkilamchi"
          onClick={yukla}
          disabled={yuklanmoqda}
        >
          {yuklanmoqda ? "…" : t("admin.rasm_yukla")}
        </Button>

        {/* Biriktirish ALOHIDA tugma: rasm yuklangani bilan u hali
            signalga bog'lanmagan. Ikkisi bir tugma bo'lsa, tasodifan
            bosilgan fayl darrov kartochkaga chiqib ketardi. */}
        {nom && (
          <form action={signalRasmiBiriktir}>
            <input type="hidden" name="id" value={signalId} />
            <input type="hidden" name="maydon" value={maydon} />
            <input type="hidden" name="nom" value={nom} />
            <Button type="submit">
              <Ikonka nom="tasdiq" className="h-4 w-4" />
            </Button>
          </form>
        )}

        {joriy && (
          <form action={signalRasmiBiriktir}>
            <input type="hidden" name="id" value={signalId} />
            <input type="hidden" name="maydon" value={maydon} />
            <input type="hidden" name="nom" value="" />
            <Button type="submit" variant="shaffof">
              {t("admin.rasm_ochir")}
            </Button>
          </form>
        )}
      </div>

      {holat && <p className="text-matn-past mt-2 text-sm">{holat}</p>}
    </div>
  );
}
