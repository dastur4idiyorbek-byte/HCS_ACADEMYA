import {
  type Tekshiruv,
  type Ustun,
  kunFarqi,
  sanaYorligi,
  shablon,
  soatYoz,
  tekshiruvSababi,
  vaqtYorligi,
  xulosaQismlari,
} from "@/lib/radar";

/** `tarjimon(til)` qaytaradigan funksiya. */
export type Tarjimon = (kalit: string) => string;

/** Radar komponentlari uchun matn yig'uvchilar — BITTA joyda.
 *
 * Kartochka, grafik va jadval bir xil yorliqlarni ishlatadi ("3-sessiya
 * 13:45", "14-okt"). Har komponent o'zicha yig'sa, bir kuni ulardan
 * biri boshqacha yozib qo'yadi va bitta sessiya ikki joyda ikki xil
 * nomlanadi.
 */

/** Tarjima bo'lsa — tarjima, bo'lmasa zaxira (masalan manba nomi
 *  bazadan kelgan xom satr). `tarjima()` topolmasa kalitni qaytaradi. */
export function tYoki(t: Tarjimon, kalit: string, zaxira: string): string {
  const m = t(kalit);
  return m === kalit ? zaxira : m;
}

/** Tekshiruv izohi: "o'rtachadan 8.2 barobar (chegara 5x)". */
export function sababMatni(t: Tarjimon, tek: Tekshiruv): string {
  const { kalit, qiymatlar } = tekshiruvSababi(tek);
  return shablon(t(`radar.sabab.${kalit}`), qiymatlar);
}

/** Manbaning odam o'qiydigan nomi. Noma'lum manba — xom holida. */
export function manbaNomi(t: Tarjimon, manba: string): string {
  if (!manba) return "—";
  return tYoki(t, `radar.manba.${manba}`, manba);
}

/** XULOSA qatori — qaysi tekshiruvlar o'tgani, guruhlarga bo'lib.
 *
 * Har doim "KUZATIB BORING — bu signal emas" bilan tugaydi: kartochka
 * qanchalik "kuchli" ko'rinmasin, u tavsiya emas.
 */
export function xulosaMatni(t: Tarjimon, tekshiruvlar: Tekshiruv[]): string {
  const { harakat, yoqilgi } = xulosaQismlari(tekshiruvlar);
  const nomlar = (kodlar: string[]) => kodlar.map((k) => t(`radar.tek.${k}`)).join(", ");
  const qismlar: string[] = [];
  if (harakat.length) qismlar.push(shablon(t("radar.xulosa_harakat"), { r: nomlar(harakat) }));
  if (yoqilgi.length) qismlar.push(shablon(t("radar.xulosa_yoqilgi"), { r: nomlar(yoqilgi) }));
  const asos = qismlar.length
    ? `${t("radar.xulosa_boshi")}: ${qismlar.join("; ")}.`
    : t("radar.xulosa_yoq");
  return `${t("radar.xulosa")}: ${asos} ${t("radar.xulosa_oxiri")}`;
}

/** Tarjimadagi qisqa oy nomlari: "yan,fev,...". */
export function oyNomlari(t: Tarjimon): string[] {
  return t("radar.oylar").split(",");
}

/** Kun yorlig'i kunlar qatori uchun: "Bugun", "Kecha", "12-okt". */
export function kunYorligi(t: Tarjimon, kun: string, bugun: string): string {
  const farq = kunFarqi(kun, bugun);
  if (farq === 0) return t("radar.bugun");
  if (farq === 1) return t("radar.kecha");
  return sanaYorligi(kun, oyNomlari(t), t("radar.kun_yorliq"));
}

/** To'liq vaqt: "14-okt 13:45" (zonada). */
export function vaqtMatni(t: Tarjimon, d: Date | null, zona: string): string {
  if (!d) return "—";
  return vaqtYorligi(d, zona, oyNomlari(t), t("radar.kun_yorliq"));
}

/** Ustun sarlavhasi: `{ustki: "14-okt", nom: "3-sessiya", soat: "13:45"}`.
 *
 * Bir kunlik oynada sana ortiqcha — u kunlar qatorida tanlangan.
 * Oylik ko'rinishda ustun — kun, soat yo'q. `asosiy` — bir qatorli
 * ko'rinish ("3-sessiya 13:45"), jadval sarlavhasi va maslahatlar uchun.
 */
export function ustunYorligi(
  t: Tarjimon,
  u: Ustun,
  zona: string,
  sanaKerak: boolean,
): { ustki: string | null; nom: string; soat: string | null; asosiy: string } {
  const sana = sanaYorligi(u.kun, oyNomlari(t), t("radar.kun_yorliq"));
  if (u.tartib === null) return { ustki: null, nom: sana, soat: null, asosiy: sana };
  const nom = shablon(t("radar.sessiya_n"), { n: u.tartib });
  const soat = soatYoz(u.vaqt, zona);
  return { ustki: sanaKerak ? sana : null, nom, soat, asosiy: `${nom} ${soat}` };
}
