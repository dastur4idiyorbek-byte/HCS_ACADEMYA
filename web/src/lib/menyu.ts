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
  { kod: "signallar", yol: "/signallar", kalit: "menyu.signallar", belgi: "📈", talab: "lite" },
  { kod: "video", yol: "/video", kalit: "menyu.video", belgi: "🎬", talab: "pro" },
  { kod: "kurs", yol: "/kurs", kalit: "menyu.kurs", belgi: "🎓", talab: null, tezKunda: true },
  { kod: "statistika", yol: "/statistika", kalit: "menyu.statistika", belgi: "📊", talab: "lite" },
  { kod: "portfel", yol: "/portfel", kalit: "menyu.portfel", belgi: "💼", talab: "lite" },
  // Shaffoflik bo'limi ATAYLAB hammaga ochiq: "nega signal yo'q" savoli
  // aynan obunasi yo'q odamda tug'iladi. Uni qulflash — ishonchni
  // qulflash bilan barobar.
  { kod: "sokinlik", yol: "/sokinlik", kalit: "menyu.sokinlik", belgi: "🔇", talab: null },
  { kod: "profil", yol: "/profil", kalit: "menyu.profil", belgi: "👤", talab: null },
  { kod: "admin", yol: "/admin", kalit: "menyu.admin", belgi: "🛠", talab: null, adminUchun: true },
];

export function korinadiganBandlar(admin: boolean): MenyuBandi[] {
  return MENYU.filter((b) => !b.adminUchun || admin);
}
