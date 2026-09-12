"use client";

import { useState, useTransition } from "react";

import { Button } from "@/components/ui/Button";
import { Ikonka } from "@/components/ui/Ikonka";

import { skanniSora } from "./amallar";

/** "Hozir yangila" — bitta qo'shimcha skanni so'raydi.
 *
 * TO'XTATISH TUGMASI YO'Q (loyiha egasining qarori): skan tugagach
 * o'zi to'xtaydi, to'xtatadigan narsa yo'q.
 *
 * Bosilgandan keyin tugma O'CHADI va xabar chiqadi. Sabab: javob
 * darrov kelmaydi (bot bayroqni bir daqiqada ko'radi), va tugma
 * faol qolsa admin uni qayta-qayta bosardi.
 */
export function YangilashTugmasi({
  matn,
  sorandi,
  izoh,
}: {
  matn: string;
  sorandi: string;
  izoh: string;
}) {
  const [yuborildi, setYuborildi] = useState(false);
  const [kutilmoqda, boshla] = useTransition();

  return (
    <div className="flex flex-col items-start gap-1.5">
      <Button
        type="button"
        variant="ikkilamchi"
        disabled={yuborildi || kutilmoqda}
        onClick={() =>
          boshla(async () => {
            await skanniSora();
            setYuborildi(true);
          })
        }
      >
        <Ikonka nom="yangilash" className="mr-1.5 h-4 w-4" />
        {yuborildi ? sorandi : matn}
      </Button>
      <p className="text-matn-past max-w-md text-xs">{izoh}</p>
    </div>
  );
}
