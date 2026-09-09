import type { Tarif } from "@/lib/queries";

/** Bosh sahifadagi vidjetlar — BITTA MANBA.
 *
 * NEGA RO'YXAT KODDA. Vidjet — kod: uni bazadan yasab bo'lmaydi,
 * chunki har biri boshqa joydan ma'lumot oladi va boshqacha
 * chiziladi. Bazada faqat FOYDALANUVCHINING TANLOVI saqlanadi:
 * qaysi vidjet, qaysi tartibda.
 *
 * Shuning uchun bu yerga yangi vidjet qo'shilsa, uni chizadigan kod
 * ham yozilishi kerak. Ikkisi ajralib qolmasin deb
 * `web/tests/vidjet.test.ts` ro'yxatni chizuvchi bilan solishtiradi.
 */
export type VidjetKod =
  | "salomatlik"
  | "oxirgi_signal"
  | "pozitsiyalar"
  | "natija"
  | "qorquv"
  | "tarif"
  | "altcoin"
  | "bozor_kapitali"
  | "yangi_dars";

export type Vidjet = {
  kod: VidjetKod;
  /** Tarjima kaliti — nomi kodda yozilmaydi. */
  kalit: string;
  /** `null` — hammaga ochiq. Aks holda shu tarif kerak. */
  talab: Tarif | null;
};

/** Hamma vidjetlar — foydalanuvchi shu ro'yxatdan tanlaydi. */
export const VIDJETLAR: Vidjet[] = [
  { kod: "salomatlik", kalit: "vidjet.salomatlik", talab: null },
  { kod: "oxirgi_signal", kalit: "vidjet.oxirgi_signal", talab: "lite" },
  { kod: "pozitsiyalar", kalit: "vidjet.pozitsiyalar", talab: "lite" },
  { kod: "natija", kalit: "vidjet.natija", talab: "lite" },
  { kod: "qorquv", kalit: "vidjet.qorquv", talab: null },
  { kod: "tarif", kalit: "vidjet.tarif", talab: null },
  { kod: "altcoin", kalit: "vidjet.altcoin", talab: null },
  { kod: "bozor_kapitali", kalit: "vidjet.bozor_kapitali", talab: null },
  { kod: "yangi_dars", kalit: "vidjet.yangi_dars", talab: null },
];

/** Yangi kelgan odamga ko'rsatiladigan OLTITA vidjet.
 *
 * NEGA OLTITA VA NEGA AYNAN SHULAR. Yangi odam birinchi ekranda
 * ikkita savolga javob izlaydi: "menda nima bo'lyapti?" va "bozor
 * qanday?". Shuning uchun uchtasi o'ziniki (tarif, pozitsiya,
 * natija), uchtasi bozorniki (salomatlik, signal, qo'rquv).
 *
 * Oltitadan ko'pi birinchi ekranga sig'maydi va tanlash o'rniga
 * shovqin bo'ladi. Xohlagan odam sozlamadan qolganini qo'shadi.
 */
export const SUKUT_VIDJETLAR: VidjetKod[] = [
  "salomatlik",
  "oxirgi_signal",
  "pozitsiyalar",
  "natija",
  "qorquv",
  "tarif",
];

/** Foydalanuvchi tanlovidan ko'rsatiladigan ro'yxatni yasaydi.
 *
 * Tanlov BO'SH bo'lsa — odam hali hech narsa tanlamagan, unga sukut
 * to'plami beriladi. Bo'sh ro'yxatni "hech narsa ko'rsatma" deb
 * tushunsak, yangi kelgan odam bo'sh sahifa ko'rardi.
 *
 * Noma'lum kod (eski, olib tashlangan vidjet) jimgina tashlanadi:
 * bazada qolib ketgan yozuv sahifani buzmasin.
 */
export function korinadiganVidjetlar(tanlov: VidjetKod[]): Vidjet[] {
  const manba = new Map(VIDJETLAR.map((v) => [v.kod, v]));
  const kerakli = tanlov.length === 0 ? SUKUT_VIDJETLAR : tanlov;
  const natija: Vidjet[] = [];
  for (const kod of kerakli) {
    const v = manba.get(kod);
    if (v) natija.push(v);
  }
  return natija;
}
