import type { IkonkaNomi } from "@/components/ui/Ikonka";
import type { Tarif } from "@/lib/queries";

/** Menyu bandlari — bitta manba.
 *
 * Botdagi `bot/keyboards.py: MENU_REQUIREMENTS` bilan bir xil mantiq:
 * band qaysi tarifni talab qilishi shu yerda yoziladi, sahifaning
 * o'zida emas. Ikki joyda yozilsa, biri o'zgarib ikkinchisi qolib
 * ketadi — menyuda ko'rinadigan, lekin ochilmaydigan bo'lim paydo
 * bo'ladi.
 */
export type MenyuBandi = {
  kod: string;
  yol: string;
  kalit: string;
  /** HCS ikonka tizimidagi nom (`components/ui/Ikonka.tsx`).
   *  Emoji EMAS: emoji har platformada boshqacha chiziladi va
   *  bizning palitramizga bo'ysunmaydi. */
  belgi: IkonkaNomi;
  /** `null` — hammaga ochiq */
  talab: Tarif | null;
  /** Faqat adminlarga ko'rinadi */
  adminUchun?: boolean;
  /** Hali tayyor emas — "Tez kunda" */
  tezKunda?: boolean;
};

export const MENYU: MenyuBandi[] = [
  { kod: "bosh", yol: "/bosh", kalit: "menyu.bosh", belgi: "bosh", talab: null },
  // Bozor holati — BIR sahifada: Bozor Salomatligi indeksi, sektorlar,
  // terminallar va coinlar. Ilgari bu uchga bo'lingan edi, lekin
  // uchalasi bitta savolning bo'laklari: "bozor hozir qanday?".
  //
  // Sahifa FAQAT KO'RSATADI: undagi hech bir raqam modulga qaytib
  // kirmaydi va signal qaroriga ta'sir qilmaydi. Eski tizimda aynan
  // shu chegara buzilgan edi.
  //
  // Eski `/salomatlik` manzili yo'naltirishga aylandi — tashqi
  // havolalar 404 bermasin.
  {
    kod: "holat",
    yol: "/bozor-holati",
    kalit: "menyu.holat",
    belgi: "bozor_holati",
    talab: null,
  },
  {
    kod: "bozor",
    yol: "/bozor",
    kalit: "menyu.bozor",
    belgi: "terminal",
    talab: null,
  },
  {
    kod: "signallar",
    yol: "/signallar",
    kalit: "menyu.signallar",
    belgi: "signallar",
    talab: "lite",
  },
  // Akademiya — o'quv bo'limining bosh sahifasi. Video va kurs
  // ro'yxat edi, boshlanish nuqtasi yo'q edi: "qayerdan boshlayman?"
  // degan savol javobsiz qolardi.
  {
    kod: "akademiya",
    yol: "/akademiya",
    kalit: "menyu.akademiya",
    belgi: "akademiya",
    talab: null,
  },
  {
    kod: "video",
    yol: "/video",
    kalit: "menyu.video",
    belgi: "video",
    talab: "pro",
  },
  {
    kod: "bilimlar",
    yol: "/bilimlar",
    kalit: "akademiya.bilimlar",
    belgi: "maqolalar",
    talab: null,
  },
  // KITOB — akademiyaning asosiy materiali, shuning uchun video va
  // kursdan OLDIN turadi: o'quvchi qayerdan boshlashni bilsin.
  {
    kod: "kitob",
    yol: "/kitob",
    kalit: "kitob.menyu",
    belgi: "kurs",
    talab: "lite",
  },
  {
    kod: "kurs",
    yol: "/kurs",
    kalit: "menyu.kurs",
    belgi: "kurs",
    talab: null,
    tezKunda: true,
  },
  // KALKULYATOR — HAMMAGA OCHIQ (`talab: null`).
  //
  // Nega obuna talab qilinmaydi: bu yerda loyihaning hech qanday
  // tahlili yo'q. Foydalanuvchi o'z raqamlarini yozadi, hisob esa
  // brauzerda bo'ladi — sotiladigan narsa emas, foydali asbob.
  {
    kod: "kalkulyator",
    yol: "/kalkulyator",
    kalit: "kalk.menyu",
    belgi: "kalkulyator",
    talab: null,
  },
  {
    kod: "statistika",
    yol: "/statistika",
    kalit: "menyu.statistika",
    belgi: "statistika",
    talab: "lite",
  },
  {
    kod: "portfel",
    yol: "/portfel",
    kalit: "menyu.portfel",
    belgi: "pul",
    talab: "lite",
  },
  {
    kod: "profil",
    yol: "/profil",
    kalit: "menyu.profil",
    belgi: "kabinet",
    talab: null,
  },
  {
    kod: "admin",
    yol: "/admin",
    kalit: "menyu.admin",
    belgi: "admin",
    talab: null,
    adminUchun: true,
  },
];

export function korinadiganBandlar(admin: boolean): MenyuBandi[] {
  return MENYU.filter((b) => !b.adminUchun || admin);
}

/** Pastki navigatsiya bo'limi — mobil ilova uslubidagi 5 ta asosiy tab.
 *
 * Har bir tab o'z sahifalarini MENYU dagi `kod` orqali ko'rsatadi —
 * yo'l ikki joyda yozilmaydi. Ro'yxatdagi BIRINCHI sahifa tabning
 * asosiy sahifasi (tab o'sha yerga olib boradi).
 */
export type PastkiTab = {
  kod: string;
  kalit: string;
  /** Shu bo'limga tegishli sahifalar — MENYU dagi kod lar.
   *  BIRINCHISI tabning asosiy sahifasi. */
  sahifalar: string[];
};

export const PASTKI_TABLAR: PastkiTab[] = [
  { kod: "bosh", kalit: "pastki.bosh", sahifalar: ["bosh"] },
  // "bozor" tabi Bozor holatiga ochiladi — Salomatlik indeksi endi
  // o'sha sahifaning eng tepasida turadi.
  {
    kod: "bozor",
    kalit: "pastki.bozor",
    sahifalar: ["holat", "bozor"],
  },
  {
    kod: "akademiya",
    kalit: "pastki.akademiya",
    sahifalar: ["akademiya", "kitob", "video", "bilimlar", "kurs"],
  },
  {
    kod: "produkt",
    kalit: "pastki.produkt",
    sahifalar: ["signallar", "kalkulyator", "statistika"],
  },
  {
    kod: "kabinet",
    kalit: "pastki.kabinet",
    sahifalar: ["profil", "portfel", "admin"],
  },
];

/** Tabning to'liq ma'lumoti: sahifalar MENYU dan olinadi.
 *
 * `adminUchun: true` band admin bo'lmaganga qaytarilmaydi — yon
 * paneldagi `korinadiganBandlar` bilan bir xil qoida. Noma'lum kod
 * (MENYU da yo'q) jimgina tashlab yuboriladi — bo'sh havola bo'lmasin.
 */
export function tabSahifalari(tab: PastkiTab, admin: boolean): MenyuBandi[] {
  const manba = new Map(MENYU.map((b) => [b.kod, b]));
  const natija: MenyuBandi[] = [];
  for (const kod of tab.sahifalar) {
    const band = manba.get(kod);
    if (!band) continue;
    if (band.adminUchun && !admin) continue;
    natija.push(band);
  }
  return natija;
}
