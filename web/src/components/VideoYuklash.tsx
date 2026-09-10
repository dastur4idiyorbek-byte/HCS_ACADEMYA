"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Ikonka } from "@/components/ui/Ikonka";

/** Admin panelda video faylni yuklash.
 *
 * NEGA `fetch` EMAS, `XMLHttpRequest`: `fetch` da yuklash JARAYONINI
 * kuzatib bo'lmaydi (`upload.onprogress` unda yo'q). Yuz megabaytlik
 * fayl yuklanayotganda hech qanday belgi bo'lmasa, admin sahifa
 * qotib qolgan deb o'ylab yopib yuboradi.
 *
 * Fayl so'rov tanasi sifatida XOM holda yuboriladi (`multipart` emas) —
 * server uni to'g'ridan-to'g'ri diskka oqizadi, xotiraga yig'maydi.
 */
export function VideoYuklash({
  darsId,
  bormi,
  matnlar,
}: {
  darsId: number;
  /** Darsda allaqachon video bormi — tugma matni shunga qarab o'zgaradi */
  bormi: boolean;
  matnlar: Record<string, string>;
}) {
  const kiritish = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [foiz, setFoiz] = useState<number | null>(null);
  const [xato, setXato] = useState<string | null>(null);

  const yubor = (fayl: File) => {
    setXato(null);
    setFoiz(0);

    const xhr = new XMLHttpRequest();
    xhr.open(
      "POST",
      `/api/admin/video?dars=${darsId}&nom=${encodeURIComponent(fayl.name)}`,
    );
    xhr.upload.onprogress = (h) => {
      if (h.lengthComputable) setFoiz(Math.round((h.loaded / h.total) * 100));
    };
    xhr.onload = () => {
      setFoiz(null);
      if (xhr.status >= 200 && xhr.status < 300) {
        if (kiritish.current) kiritish.current.value = "";
        // Sahifa serverda qayta chiziladi — "video bor" belgisi va
        // pleyer darrov yangilanadi.
        router.refresh();
        return;
      }
      let xabar = `Xato ${xhr.status}`;
      try {
        xabar = JSON.parse(xhr.responseText).xato ?? xabar;
      } catch {
        // Javob JSON emas (masalan proksi xatosi) — holat kodi qoladi
      }
      setXato(xabar);
    };
    xhr.onerror = () => {
      setFoiz(null);
      setXato(matnlar.tarmoq_xatosi);
    };
    xhr.send(fayl);
  };

  return (
    <div className="mt-3">
      <label className="block">
        <span className="text-matn-past mb-1 block text-xs uppercase">
          {bormi ? matnlar.almashtir : matnlar.yukla}
        </span>
        <input
          ref={kiritish}
          type="file"
          accept="video/mp4,video/webm,video/quicktime,.mp4,.m4v,.webm,.mov"
          disabled={foiz !== null}
          onChange={(e) => {
            const fayl = e.target.files?.[0];
            if (fayl) yubor(fayl);
          }}
          className="text-matn-past file:border-ramka file:bg-panel file:text-sarlavha file:rounded-tugma w-full text-sm file:mr-3 file:cursor-pointer file:border file:px-3 file:py-1.5 file:text-sm"
        />
      </label>

      {foiz !== null && (
        <div className="mt-2">
          <div className="bg-fon rounded-kichik h-2 w-full overflow-hidden">
            <div
              className="bg-sarlavha h-full transition-[width]"
              style={{ width: `${foiz}%` }}
            />
          </div>
          <p className="text-matn-past raqam mt-1 text-xs">
            {matnlar.yuklanmoqda} {foiz}%
          </p>
        </div>
      )}

      {xato && (
        <p className="border-past/60 text-past rounded-kichik mt-2 border px-3 py-2 text-sm">
          <Ikonka nom="ogohlantirish" className="inline h-4 w-4 align-[-3px]" />{" "}
          {xato}
        </p>
      )}
    </div>
  );
}
