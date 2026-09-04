"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { tarjimon } from "@/lib/i18n";

import { boshPostNashr } from "../amallar";

/** Post yozish formasi — fayl AVVAL yuklanadi, keyin post yaratiladi.
 *
 * NEGA IKKI QADAM. Server amali (server action) FormData ni butunlay
 * xotiraga yig'adi. 25 MB lik audio uchun bu — 25 MB operativ xotira
 * va Next.js ning o'z chegarasi (1 MB) allaqachon to'sib qo'yardi.
 * Shuning uchun fayl alohida yo'l orqali diskka yoziladi, formaga esa
 * faqat NOMI tushadi.
 */
export function PostYuklagich({ til }: { til: "uz" | "ru" }) {
  const t = tarjimon(til);
  const [nom, setNom] = useState<string | null>(null);
  const [holat, setHolat] = useState<string | null>(null);
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const faylRef = useRef<HTMLInputElement>(null);

  async function fayliniYukla(): Promise<void> {
    const fayl = faylRef.current?.files?.[0];
    if (!fayl) return;

    setYuklanmoqda(true);
    setHolat(null);
    try {
      const javob = await fetch(
        `/api/admin/post-media?nom=${encodeURIComponent(fayl.name)}`,
        { method: "POST", body: fayl },
      );
      const natija = (await javob.json()) as { nom?: string; xato?: string };
      if (!javob.ok || !natija.nom) {
        setHolat(natija.xato ?? t("admin.post_yuklanmadi"));
        return;
      }
      setNom(natija.nom);
      setHolat(t("admin.post_yuklandi"));
    } catch {
      setHolat(t("admin.post_yuklanmadi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  return (
    <form action={boshPostNashr} className="mt-3 space-y-3">
      <label className="block">
        <span className="text-matn-past mb-1 block text-xs uppercase">
          {t("admin.post_matn")}
        </span>
        <textarea
          name="matn"
          rows={4}
          placeholder={t("admin.post_matn_joy")}
          className="border-ramka-yumshoq rounded-tugma bg-fon w-full border px-3 py-2 text-sm"
        />
      </label>

      <div className="flex flex-wrap items-end gap-2">
        <label className="min-w-0 flex-1">
          <span className="text-matn-past mb-1 block text-xs uppercase">
            {t("admin.post_fayl")}
          </span>
          <input
            ref={faylRef}
            type="file"
            accept="image/*,audio/*"
            onChange={() => {
              setNom(null);
              setHolat(null);
            }}
            className="text-matn-past w-full text-sm"
          />
        </label>
        <Button
          type="button"
          variant="ikkilamchi"
          onClick={fayliniYukla}
          disabled={yuklanmoqda}
        >
          {yuklanmoqda ? t("admin.post_yuklanmoqda") : t("admin.post_yukla")}
        </Button>
      </div>

      {holat && <p className="text-matn-past text-sm">{holat}</p>}
      {/* Fayl nomi formaga YASHIRIN maydon bo'lib tushadi — post
          yozuvi shu nomni saqlaydi, faylning o'zini emas. */}
      <input type="hidden" name="media" value={nom ?? ""} />

      <Button type="submit">{t("admin.post_nashr")}</Button>
    </form>
  );
}
