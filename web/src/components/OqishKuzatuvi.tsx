"use client";

import { useEffect, useRef } from "react";

/** Maqola qayergacha o'qilganini yozib boradi.
 *
 * NEGA KERAK. "Davom ettirish" kartochkasi kimning qayerda
 * qolganini bilishi shart; ansiz uzun maqolani bo'lib o'qib
 * bo'lmaydi.
 *
 * O'LCHOV — SAHIFA SURILISHI. Video uchun vaqt aniqroq, maqola
 * uchun esa "qayergacha yetdi" degan o'lchov aynan shu.
 *
 * NEGA HAR SURILISHDA YOZILMAYDI. Sahifa surilganda hodisa
 * soniyasiga o'nlab marta keladi. Har biriga so'rov yuborilsa,
 * bitta maqolani o'qish yuzlab yozuvga aylanardi. Shuning uchun:
 *
 *   - eng katta qiymat XOTIRADA to'planadi
 *   - serverga har o'n soniyada BIR MARTA yuboriladi
 *   - va sahifa yopilayotganda oxirgi marta
 *
 * Foiz faqat OLDINGA yuradi (serverda ham shunday): odam tepaga
 * qaytsa, "72%" birdan "10%" ga tushib ketmasin.
 */
export function OqishKuzatuvi({ kontentId }: { kontentId: number }) {
  const engKatta = useRef(0);
  const yuborilgan = useRef(0);

  useEffect(() => {
    function olcha() {
      const balandlik =
        document.documentElement.scrollHeight - window.innerHeight;
      // Sahifa ekrandan kalta — o'qilgan hisoblanadi.
      const foiz =
        balandlik <= 0
          ? 100
          : Math.round((window.scrollY / balandlik) * 100);
      engKatta.current = Math.min(100, Math.max(engKatta.current, foiz));
    }

    function yubor() {
      if (engKatta.current <= yuborilgan.current) return;
      yuborilgan.current = engKatta.current;
      // `keepalive` — sahifa yopilayotganda ham so'rov yetib borsin.
      void fetch("/api/ilgarilash", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ kontentId, foiz: engKatta.current }),
        keepalive: true,
      }).catch(() => {
        // Jim: o'qish holati — qo'shimcha qulaylik, maqolaning o'zi
        // emas. Xato xabari o'qishga xalaqit berardi.
      });
    }

    olcha();
    window.addEventListener("scroll", olcha, { passive: true });
    const taymer = setInterval(yubor, 10_000);
    window.addEventListener("pagehide", yubor);

    return () => {
      window.removeEventListener("scroll", olcha);
      window.removeEventListener("pagehide", yubor);
      clearInterval(taymer);
      yubor();
    };
  }, [kontentId]);

  return null;
}
