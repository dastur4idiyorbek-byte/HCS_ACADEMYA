import type { SVGProps } from "react";

import { cn } from "@/lib/cn";

/** HCS ikonka tizimi — BITTA manba.
 *
 * NEGA EMOJI EMAS. Emoji har platformada boshqacha chiziladi:
 * Androidda bir xil, iPhone'da boshqacha, Windows'da uchinchi xil.
 * Ranglari ham tizimniki — bizning ko'k-turkuaz palitramizga
 * bo'ysunmaydi va qorong'i fonda ba'zilari umuman ko'rinmaydi.
 *
 * SVG esa `currentColor` ni meros oladi: ikonka qaysi matn rangida
 * tursa, o'sha rangda chiziladi. Faol tab yorqin, nofaol xira —
 * qo'shimcha kodsiz.
 *
 * BITTA USLUB: hammasi 24×24 to'rda, chiziq (`stroke`) bilan,
 * yumaloq uchli. Yangi ikonka qo'shilganda shu qoidaga bo'ysunishi
 * shart — aks holda to'plam "bir joydan yig'ilgan" ko'rinishini
 * yo'qotadi.
 *
 * NOM UZBEKCHA va MA'NO bo'yicha (`sektorlar`), shakl bo'yicha emas
 * (`layers`). Sabab: ertaga sektor ikonkasi boshqa shaklga
 * o'zgarsa, uni chaqirgan yigirmata joy o'zgarmasligi kerak.
 */

const S = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

const CHIZMALAR = {
  // ---- Asosiy bo'limlar (pastki navigatsiya) ----
  bosh: (
    <>
      <path d="m3 9.5 9-6.5 9 6.5V20a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 20z" />
      <path d="M9.5 21.5v-7h5v7" />
    </>
  ),
  bozor_holati: (
    <>
      <path d="M3 3v16.5A1.5 1.5 0 0 0 4.5 21H21" />
      <path d="m7 15 4-4.5 3 2.5 5-6" />
      <path d="M19 7h-3.5M19 7v3.5" />
    </>
  ),
  akademiya: (
    <>
      <path d="M12 6.5C10.5 5.2 8.6 4.5 6 4.5H3.5v13H6c2.6 0 4.5.7 6 2 1.5-1.3 3.4-2 6-2h2.5v-13H18c-2.6 0-4.5.7-6 2z" />
      <path d="M12 6.5v13" />
    </>
  ),
  produkt: (
    <>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
    </>
  ),
  kabinet: (
    <>
      <circle cx="12" cy="8" r="3.75" />
      <path d="M4.5 20.5a7.5 7.5 0 0 1 15 0" />
    </>
  ),

  // ---- Bosh sahifa ichidagi ----
  malumot: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5.5M12 7.75v.25" />
    </>
  ),
  maqolalar: (
    <>
      <path d="M6 3.5h8L18.5 8v12.5A1 1 0 0 1 17.5 21h-11a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z" />
      <path d="M14 3.5V8h4.5" />
      <path d="M8.5 13h7M8.5 16.5h5" />
    </>
  ),
  media: (
    <>
      <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
      <circle cx="8.75" cy="9.75" r="1.5" />
      <path d="m4.5 17 4.75-4.75L14 17M13 14l2.5-2.5 4 4" />
    </>
  ),
  video: (
    <>
      <rect x="3.5" y="4.5" width="17" height="15" rx="3" />
      <path d="m10.5 9 5 3-5 3z" />
    </>
  ),
  audio: (
    <>
      <path d="M4 11v2M7.5 8.5v7M11 5.5v13M14.5 8.5v7M18 10v4M21 11.5v1" />
    </>
  ),
  fayllar: (
    <>
      <path d="M6 3.5h8L18.5 8v12.5A1 1 0 0 1 17.5 21h-11a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z" />
      <path d="M14 3.5V8h4.5" />
    </>
  ),
  havolalar: (
    <>
      <path d="M10 14a4 4 0 0 0 5.66 0l3-3A4 4 0 0 0 13 5.34l-1.2 1.2" />
      <path d="M14 10a4 4 0 0 0-5.66 0l-3 3A4 4 0 0 0 11 18.66l1.2-1.2" />
    </>
  ),
  elonlar: (
    <>
      <path d="M4 10v4a1 1 0 0 0 1 1h2.5l6 4V5l-6 4H5a1 1 0 0 0-1 1z" />
      <path d="M17.5 9.5a3.5 3.5 0 0 1 0 5M20 7a7 7 0 0 1 0 10" />
    </>
  ),

  // ---- Bozor holati ----
  salomatlik: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M7 12h2l1.5-3.5L13 15l1.5-3H17" />
    </>
  ),
  sektorlar: (
    <>
      <path d="m12 3 8.5 4.5L12 12 3.5 7.5z" />
      <path d="m3.5 12 8.5 4.5 8.5-4.5" />
      <path d="m3.5 16.5 8.5 4.5 8.5-4.5" />
    </>
  ),
  blokcheyn: (
    <>
      <path d="m12 2.5 4 2.25v4.5L12 11.5 8 9.25v-4.5z" />
      <path d="m6 12.5 4 2.25v4.5L6 21.5l-4-2.25v-4.5z" />
      <path d="m18 12.5 4 2.25v4.5l-4 2.25-4-2.25v-4.5z" />
    </>
  ),
  terminal: (
    <>
      <rect x="3" y="4.5" width="18" height="15" rx="2" />
      <path d="M3 9h18" />
      <path d="m7 15 2.5-2.5L12 15l4-4.5" />
    </>
  ),
  coinlar: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7v10M14.5 9.5a2.5 2.5 0 0 0-2.5-1.5h-.5a2 2 0 0 0 0 4h1a2 2 0 0 1 0 4H12a2.5 2.5 0 0 1-2.5-1.5" />
    </>
  ),
  onchain: (
    <>
      <circle cx="17.5" cy="6" r="2.5" />
      <circle cx="17.5" cy="18" r="2.5" />
      <circle cx="6" cy="12" r="2.5" />
      <path d="m8.3 10.9 6.9-3.4M8.3 13.1l6.9 3.4" />
    </>
  ),
  grafik: (
    <>
      <path d="M7.5 4v3M7.5 17v3M16.5 3v4M16.5 15v4" />
      <rect x="5" y="7" width="5" height="10" rx="1" />
      <rect x="14" y="7" width="5" height="8" rx="1" />
    </>
  ),

  // ---- Akademiya ----
  kurs: (
    <>
      <path d="M4.5 4.5A1.5 1.5 0 0 1 6 3h11.5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H6a1.5 1.5 0 0 0 0 3h12.5" />
      <path d="M9.5 3v7l2.25-1.75L14 10V3" />
    </>
  ),
  testlar: (
    <>
      <rect x="4" y="3.5" width="16" height="17" rx="2" />
      <path d="m8.5 11.5 2.25 2.25L15.5 9" />
    </>
  ),
  progress: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="3.75" />
      <path d="m14.5 9.5 5-5M17 4.25 19.5 4.5l.25 2.5" />
    </>
  ),
  amaliyot: (
    <>
      <path d="M3 20.5h18" />
      <path d="m6 16 4-4.5 3 2.5 5.5-6.5" />
      <path d="M19.5 7.5h-3.5M19.5 7.5V11" />
    </>
  ),

  // ---- Produkt ----
  signallar: (
    <>
      <path d="M3.5 20.5h17" />
      <path d="m6 15.5 4-4 3 2.5 5-5.5" />
      <path d="M18 8.5h-3M18 8.5v3" />
    </>
  ),
  tahlillar: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 5 5" />
      <path d="M8 12V9.5M10.5 12V7.5M13 12v-3" />
    </>
  ),
  statistika: (
    <>
      <path d="M4.5 20.5h15" />
      <path d="M7 17V9.5M11 17V4.5M15 17v-5M19 17v-9" />
    </>
  ),

  // ---- Signal kartasi ----
  kirish_zonasi: (
    <>
      <path d="M13.5 4.5H6a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 6 19.5h12a1.5 1.5 0 0 0 1.5-1.5v-7.5" />
      <path d="M14 10 20.5 3.5M20.5 3.5h-4.25M20.5 3.5v4.25" />
    </>
  ),
  tp: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.9" fill="currentColor" stroke="none" />
    </>
  ),
  stop: (
    <>
      <path d="M12 3 5 5.5v6c0 4 3 7.5 7 9.5 4-2 7-5.5 7-9.5v-6z" />
      <path d="m9.75 9.75 4.5 4.5M14.25 9.75l-4.5 4.5" />
    </>
  ),

  // ---- Signal holati ----
  kutilmoqda: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  faol: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </>
  ),
  bekor: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m9.25 9.25 5.5 5.5M14.75 9.25l-5.5 5.5" />
    </>
  ),
  zaiflashmoqda: (
    <>
      <path d="M12 4 2.5 20h19z" />
      <path d="M12 10v4M12 17.25v.25" />
    </>
  ),

  // ---- Tahlil va grafik elementlari ----
  trend: (
    <>
      <path d="m3.5 17.5 5.5-6 3.5 3 8-9" />
      <path d="M20.5 5.5h-4M20.5 5.5v4" />
    </>
  ),
  hajm: (
    <>
      <path d="M3.5 20.5h17" />
      <path d="M7 17.5v-5M11 17.5v-9M15 17.5v-3M19 17.5v-7" />
    </>
  ),
  jadval: (
    <>
      <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
      <path d="M3.5 9.5h17M9.5 9.5v10M15 9.5v10" />
    </>
  ),
  quote: (
    <>
      <path d="M9.5 6.5C6.5 8 5 10 5 12.5v5h5.5V12H8c0-1.75.5-3 2.5-4z" />
      <path d="M19 6.5c-3 1.5-4.5 3.5-4.5 6v5H20V12h-2.5c0-1.75.5-3 2.5-4z" />
    </>
  ),
  ogohlantirish: (
    <>
      <path d="M12 4 2.5 20h19z" />
      <path d="M12 10v4M12 17.25v.25" />
    </>
  ),

  // ---- Kurs va o'quv jarayoni ----
  sertifikat: (
    <>
      <circle cx="12" cy="9.5" r="5.5" />
      <path d="m8.5 14-1 7 4.5-2.5L16.5 21l-1-7" />
    </>
  ),
  muddat: (
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
      <path d="M3.5 10h17M8 3.5V7M16 3.5V7" />
    </>
  ),

  // ---- Foydalanuvchi va kabinet ----
  xavfsizlik: (
    <>
      <path d="M12 3 5 5.5v6c0 4 3 7.5 7 9.5 4-2 7-5.5 7-9.5v-6z" />
      <path d="m9 12 2.25 2.25L15.5 10" />
    </>
  ),
  bildirishnoma: (
    <>
      <path d="M18 10a6 6 0 1 0-12 0c0 4-1.5 5.5-1.5 5.5h15S18 14 18 10z" />
      <path d="M10.25 19a2 2 0 0 0 3.5 0" />
    </>
  ),
  sozlamalar: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.5 12a7.6 7.6 0 0 0-.15-1.5l2-1.55-2-3.45-2.35 1a7.5 7.5 0 0 0-2.6-1.5L14 2.5h-4l-.4 2.5a7.5 7.5 0 0 0-2.6 1.5l-2.35-1-2 3.45 2 1.55a7.6 7.6 0 0 0 0 3l-2 1.55 2 3.45 2.35-1a7.5 7.5 0 0 0 2.6 1.5l.4 2.5h4l.4-2.5a7.5 7.5 0 0 0 2.6-1.5l2.35 1 2-3.45-2-1.55c.1-.49.15-.99.15-1.5z" />
    </>
  ),
  chiqish: (
    <>
      <path d="M14.5 4.5H6A1.5 1.5 0 0 0 4.5 6v12A1.5 1.5 0 0 0 6 19.5h8.5" />
      <path d="M15 12h6.5M18.5 8.5 22 12l-3.5 3.5" />
    </>
  ),

  // ---- Qo'shimcha ----
  qidiruv: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  filtr: (
    <>
      <path d="M3.5 5.5h17l-6.5 7.5v6l-4 2v-8z" />
    </>
  ),
  saralash: (
    <>
      <path d="M20 8.5a8 8 0 1 0-1 8" />
      <path d="M20.5 3.5v5h-5" />
    </>
  ),
  yangilash: (
    <>
      <path d="M20 8.5a8 8 0 1 0-1 8" />
      <path d="M20.5 3.5v5h-5" />
    </>
  ),
  korish: (
    <>
      <path d="M1.5 12S5.5 5.5 12 5.5 22.5 12 22.5 12 18.5 18.5 12 18.5 1.5 12 1.5 12z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),

  // ---- Holat va boshqa belgilar ----
  himoya: (
    <>
      <path d="M12 3 5 5.5v6c0 4 3 7.5 7 9.5 4-2 7-5.5 7-9.5v-6z" />
    </>
  ),
  premium: (
    <>
      <path d="m12 3 2.75 5.75L21 9.5l-4.5 4.35L17.6 20 12 17l-5.6 3 1.1-6.15L3 9.5l6.25-.75z" />
    </>
  ),
  yangilangan: (
    <>
      <path d="M12 4.5v15M4.5 12h15" />
    </>
  ),
  qulf: (
    <>
      <rect x="4.5" y="10.5" width="15" height="10" rx="2" />
      <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
    </>
  ),
  tasdiq: (
    <>
      <path d="m5 12.5 4.5 4.5L19 6.5" />
    </>
  ),
  yopish: (
    <>
      <path d="m6 6 12 12M18 6 6 18" />
    </>
  ),
  qosh: (
    <>
      <path d="M12 5v14M5 12h14" />
    </>
  ),
  tepaga: (
    <>
      <path d="M12 19V5M6 11l6-6 6 6" />
    </>
  ),
  pastga: (
    <>
      <path d="M12 5v14M6 13l6 6 6-6" />
    </>
  ),
  ochish: (
    <>
      <path d="M5 12h13M13 7l5 5-5 5" />
    </>
  ),
  pul: (
    <>
      <rect x="2.5" y="6" width="19" height="12" rx="2" />
      <circle cx="12" cy="12" r="2.75" />
      <path d="M6 12h.01M18 12h.01" />
    </>
  ),
  kalkulyator: (
    <>
      <rect x="5" y="2.5" width="14" height="19" rx="2" />
      <path d="M8 6.5h8" />
      <path d="M9 11h.01M12 11h.01M15 11h.01M9 14.5h.01M12 14.5h.01M15 14.5h.01M9 18h.01M12 18h.01M15 18h.01" />
    </>
  ),
  zanjir: (
    <>
      <rect x="2.5" y="9" width="7" height="6" rx="2" />
      <rect x="14.5" y="9" width="7" height="6" rx="2" />
      <path d="M9.5 12h5" />
    </>
  ),
  narx: (
    <>
      <path d="M20.5 12.5 12.5 20.5a2 2 0 0 1-2.83 0l-6.17-6.17a2 2 0 0 1-.5-1.33V5a1.5 1.5 0 0 1 1.5-1.5h7.5a2 2 0 0 1 1.41.59l7.09 7.09a1.65 1.65 0 0 1 0 1.32z" />
      <path d="M7.5 7.5h.01" />
    </>
  ),
  diniy: (
    <>
      <path d="M16 4.5a8 8 0 1 0 0 15 6.5 6.5 0 1 1 0-15z" />
      <path d="m19 8.5.9 2.1 2.1.4-1.5 1.6.3 2.3-1.8-1-1.8 1 .3-2.3L16 11l2.1-.4z" />
    </>
  ),
  admin: (
    <>
      <path d="m14.5 6.5 3 3M4 20l1-4 9.5-9.5a2.12 2.12 0 0 1 3 3L8 19z" />
      <path d="M4 20h5" />
    </>
  ),
  telegram: (
    <>
      <path d="m21.5 4.5-3 15-6-4.5-3 3v-4.5l8-8-10 6-5-1.5z" />
    </>
  ),
  instagram: (
    <>
      <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <path d="M16.75 7.25h.01" />
    </>
  ),
  youtube: (
    <>
      <rect x="2.5" y="5.5" width="19" height="13" rx="4" />
      <path d="m10.5 9.25 5 2.75-5 2.75z" />
    </>
  ),
  tarmoq: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.7 2.5 15.3 0 18M12 3c-2.5 2.7-2.5 15.3 0 18" />
    </>
  ),
} satisfies Record<string, React.ReactNode>;

export type IkonkaNomi = keyof typeof CHIZMALAR;

export const IKONKA_NOMLARI = Object.keys(CHIZMALAR) as IkonkaNomi[];

export function ikonkaBormi(nom: string): nom is IkonkaNomi {
  return nom in CHIZMALAR;
}

/** Bitta ikonka.
 *
 * `aria-hidden` — STANDART holat. Ikonka deyarli doim matn yonida
 * turadi va ekran o'qigich uni ikkinchi marta aytishi kerak emas.
 * Yolg'iz turgan ikonka uchun `nomi` beriladi va u `<title>` ga
 * aylanadi — o'shanda ikonka o'qiladi.
 *
 * O'LCHAM CSS DAN: `w-5 h-5` kabi sinf bilan. `width`/`height`
 * atributlari qo'yilmadi — aks holda har chaqiruvda ikkita joyda
 * (atribut va sinf) o'lcham yozilib, ular bir-biriga zid bo'lardi.
 */
export function Ikonka({
  nom,
  nomi,
  className,
  ...qolgan
}: {
  nom: IkonkaNomi;
  /** Ekran o'qigich uchun matn. Berilmasa, ikonka yashiriladi. */
  nomi?: string;
} & Omit<SVGProps<SVGSVGElement>, "nom">) {
  // STANDART O'LCHAM faqat chaqiruvchi o'zi bermagan bo'lsa.
  //
  // NEGA SHART KERAK. `cn()` — oddiy birlashtiruvchi, u Tailwind
  // sinflarini SOLISHTIRMAYDI (`tailwind-merge` emas). Ya'ni
  // "h-5 w-5" va "h-4 w-4" ikkalasi ham chiqib ketardi va qaysi biri
  // g'olib bo'lishini sinf tartibi emas, CSS faylidagi tartib hal
  // qilardi — natijada kichik ikonka so'ralgan joyda ham katta
  // ikonka chizilardi. Xato jimgina: konsolda hech narsa yozilmaydi.
  const olchamBor = /(^|\s)(h|w|size)-/.test(className ?? "");
  return (
    <svg
      viewBox="0 0 24 24"
      role={nomi ? "img" : undefined}
      aria-hidden={nomi ? undefined : true}
      className={cn(olchamBor ? null : "h-5 w-5", "shrink-0", className)}
      {...S}
      {...qolgan}
    >
      {nomi && <title>{nomi}</title>}
      {CHIZMALAR[nom]}
    </svg>
  );
}
