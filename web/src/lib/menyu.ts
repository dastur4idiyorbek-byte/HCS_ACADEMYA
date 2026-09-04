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
  belgi: string;
  /** `null` — hammaga ochiq */
  talab: Tarif | null;
  /** Faqat adminlarga ko'rinadi */
  adminUchun?: boolean;
  /** Hali tayyor emas — "Tez kunda" */
  tezKunda?: boolean;
};

export const MENYU: MenyuBandi[] = [
  { kod: "bosh", yol: "/bosh", kalit: "menyu.bosh", belgi: "🏠", talab: null },
  // Bozor Salomatligi Bosh sahifadan keyin turadi: u tizimning markaziy
  // ko'rsatkichi. "Nega signal yo'q?" endi ALOHIDA band emas — uning
  // mazmuni shu sahifaning ikkinchi yarmi, chunki ikkalasi bitta
  // savolning ikki yarmi: "bozor qanday?" va "shuning uchun bugun nima
  // bo'ldi?".
  // Bozor ko'rinishi — haftalik va kunlik qarash. SIGNAL EMAS:
  // loyiha egasining sharti bo'yicha asosiy tahlil 4 soatlikda
  // qoladi, bu sahifa esa umumiy manzarani ko'rsatadi.
  { kod: "bozor", yol: "/bozor", kalit: "menyu.bozor", belgi: "🌍", talab: null },
  { kod: "signallar", yol: "/signallar", kalit: "menyu.signallar", belgi: "📈", talab: "lite" },
  { kod: "video", yol: "/video", kalit: "menyu.video", belgi: "🎬", talab: "pro" },
  { kod: "kurs", yol: "/kurs", kalit: "menyu.kurs", belgi: "🎓", talab: null, tezKunda: true },
  { kod: "statistika", yol: "/statistika", kalit: "menyu.statistika", belgi: "📊", talab: "lite" },
  { kod: "portfel", yol: "/portfel", kalit: "menyu.portfel", belgi: "💼", talab: "lite" },
  { kod: "profil", yol: "/profil", kalit: "menyu.profil", belgi: "👤", talab: null },
  { kod: "admin", yol: "/admin", kalit: "menyu.admin", belgi: "🛠", talab: null, adminUchun: true },
];

export function korinadiganBandlar(admin: boolean): MenyuBandi[] {
  return MENYU.filter((b) => !b.adminUchun || admin);
}
