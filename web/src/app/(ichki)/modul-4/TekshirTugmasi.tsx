"use client";

import { useState, useTransition } from "react";

import { Button } from "@/components/ui/Button";
import { Ikonka } from "@/components/ui/Ikonka";

import { radarniSora } from "./amallar";

/** "Hozir tekshir" — bitta qo'lda tekshiruvni so'raydi.
 *
 * `kuzatuv/YangilashTugmasi.tsx` bilan bir xil xulq: bosilgach tugma
 * O'CHADI, chunki javob darrov kelmaydi (bot bayroqni keyingi
 * aylanishda ko'radi) va faol tugmani admin qayta-qayta bosardi.
 *
 * `soralgan` — bazada bayroq allaqachon turibdi (boshqa oynada yoki
 * avval bosilgan): tugma boshidanoq o'chiq.
 */
export function TekshirTugmasi({
  matn,
  soraldi,
  izoh,
  soralgan,
}: {
  matn: string;
  soraldi: string;
  izoh: string;
  soralgan: boolean;
}) {
  const [yuborildi, setYuborildi] = useState(false);
  const [kutilmoqda, boshla] = useTransition();
  const ochiq = yuborildi || soralgan;

  return (
    <div className="flex flex-col items-start gap-1.5">
      <Button
        type="button"
        variant="ikkilamchi"
        disabled={ochiq || kutilmoqda}
        onClick={() =>
          boshla(async () => {
            await radarniSora();
            setYuborildi(true);
          })
        }
      >
        <Ikonka nom="yangilash" className="mr-1.5 h-4 w-4" />
        {ochiq ? soraldi : matn}
      </Button>
      <p className="text-matn-past max-w-xs text-xs">{izoh}</p>
    </div>
  );
}
