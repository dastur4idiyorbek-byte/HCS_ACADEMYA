/** Yopilgan signalning TAHLIL qatori — sof hisob.
 *
 * Nima uchun alohida modul: bu raqamlar (Stop masofasi, R/R nisbati,
 * ushlab turish vaqti) sahifada hisoblansa, ularni test qilib
 * bo'lmasdi. Ular esa strategiya haqidagi XULOSAGA asos bo'ladi —
 * noto'g'ri formula noto'g'ri qarorga olib boradi.
 */

export type Yakun = "tp2" | "tp1_stop" | "stop" | "bekor";

export type Tahlil = {
  /** Stop kirish nuqtasidan necha foiz pastda edi */
  stopFoiz: number | null;
  /** TP2 gacha necha foiz */
  tp2Foiz: number | null;
  /** R/R: TP2 masofasi / Stop masofasi. Signalning va'dasi. */
  nisbat: number | null;
  /** Signal necha soat ochiq turdi */
  soat: number | null;
  yakun: Yakun;
};

export function yakuni(holat: string, tp1Olindi: boolean): Yakun {
  if (holat === "tp2_hit") return "tp2";
  if (holat === "cancelled") return "bekor";
  if (holat === "stopped") return tp1Olindi ? "tp1_stop" : "stop";
  // Muddat bo'yicha yopilish — pozitsiya OCHILGAN edi, ya'ni
  // "bekor" emas. Natijasi foyda ham, zarar ham bo'lishi mumkin,
  // shuning uchun u TP1 olinganiga qarab ajratiladi.
  if (holat === "timed_out") return tp1Olindi ? "tp1_stop" : "stop";
  return "bekor";
}

export function tahlil(s: {
  status: string;
  entry: number;
  stop: number;
  tp2: number;
  tp1Reached: boolean;
  createdAt: Date | null;
  closedAt: Date | null;
}): Tahlil {
  const yaroqli = s.entry > 0;
  const stopFoiz = yaroqli && s.stop > 0 ? ((s.entry - s.stop) / s.entry) * 100 : null;
  const tp2Foiz = yaroqli && s.tp2 > 0 ? ((s.tp2 - s.entry) / s.entry) * 100 : null;

  return {
    stopFoiz,
    tp2Foiz,
    // Nisbat faqat ikkalasi ham musbat bo'lganda ma'noga ega. Stop nolga
    // teng bo'lsa bo'linma cheksizga ketardi va ekranda "Infinity"
    // chiqardi — bu raqam emas, xato.
    nisbat:
      stopFoiz !== null && tp2Foiz !== null && stopFoiz > 0 ? tp2Foiz / stopFoiz : null,
    soat:
      s.createdAt && s.closedAt
        ? (s.closedAt.getTime() - s.createdAt.getTime()) / 3_600_000
        : null,
    yakun: yakuni(s.status, s.tp1Reached),
  };
}

/** Bir necha signalning umumiy ko'rsatkichi.
 *
 * WIN-RATE da BEKOR QILINGANLAR hisobga kirmaydi: ular savdoga
 * aylanmagan, ya'ni na yutuq, na yutqazish. Ularni maxrajga qo'shsak,
 * ko'rsatkich sun'iy ravishda pasayardi.
 */
export function xulosa(qatorlar: { yakun: Yakun; natijaFoiz: number | null }[]): {
  savdo: number;
  yutuq: number;
  winRate: number | null;
  ortachaNatija: number | null;
  jamiFoiz: number;
} {
  const savdolar = qatorlar.filter((q) => q.yakun !== "bekor");
  const natijalar = savdolar
    .map((q) => q.natijaFoiz)
    .filter((x): x is number => x !== null);
  const yutuq = natijalar.filter((x) => x > 0).length;

  return {
    savdo: savdolar.length,
    yutuq,
    winRate: natijalar.length > 0 ? (yutuq / natijalar.length) * 100 : null,
    ortachaNatija:
      natijalar.length > 0
        ? natijalar.reduce((a, b) => a + b, 0) / natijalar.length
        : null,
    jamiFoiz: natijalar.reduce((a, b) => a + b, 0),
  };
}

/** R/R nisbatida zarar qilmaslik uchun kerakli win-rate.
 *
 * 1:1.5 nisbatda 40% yetarli, 1:3 da 25%. Bu raqam ekranda haqiqiy
 * win-rate yonida turadi — "20% yomonmi?" degan savolga javob
 * nisbatsiz berilmaydi.
 */
export function kerakliWinRate(nisbat: number): number | null {
  if (!Number.isFinite(nisbat) || nisbat <= 0) return null;
  return (1 / (1 + nisbat)) * 100;
}
