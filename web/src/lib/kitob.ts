/** Kitob haqidagi yagona manba — sahifa ham, yuklash yo'li ham shundan o'qiydi. */

import type { Tarif } from "@/lib/queries";

/** PDF fayl nomi. `scripts/kitob/qur.py` shu nom bilan yasaydi. */
export const KITOB_FAYLI = "HCS_Academy_Noldan_kripto_savdogariga.pdf";

/** Yuklab olish uchun kerakli eng kam tarif.
 *
 * `lite` — akademiyaning asosi. Video darsliklar `pro` talab qiladi;
 * kitob esa boshlang'ich material, shuning uchun undan yengilroq
 * darvoza. O'zgartirish kerak bo'lsa — FAQAT shu yerda. */
export const KITOB_TARIFI: Tarif = "lite";

/** Kitob tarkibi — sahifada ko'rsatiladigan bo'limlar.
 *
 * KALITLAR `scripts/kitob/eksport.py` dagi ro'yxat bilan BIR XIL
 * bo'lishi shart: sayt bo'limni shu kalit bo'yicha topadi. Test
 * ikkalasini solishtirib turadi. */
export const KITOB_BOLIMLARI = [
  { kalit: "kirish", boblar: "—" },
  { kalit: "asoslar", boblar: "1–7" },
  { kalit: "fundamental", boblar: "8–10" },
  { kalit: "texnik", boblar: "11–16" },
  { kalit: "smc", boblar: "17–18" },
  { kalit: "ict", boblar: "19–20" },
  { kalit: "risk", boblar: "21–23" },
  { kalit: "yakun", boblar: "24" },
] as const;

/** Bo'limning oldingi va keyingi qo'shnisi — sahifa oxiridagi
 *  «keyingi bo'lim» havolasi uchun. */
export function bolimYonidagi(kalit: string): {
  oldingi: string | null;
  keyingi: string | null;
} {
  const i = KITOB_BOLIMLARI.findIndex((b) => b.kalit === kalit);
  return {
    oldingi: i > 0 ? KITOB_BOLIMLARI[i - 1].kalit : null,
    keyingi:
      i >= 0 && i < KITOB_BOLIMLARI.length - 1
        ? KITOB_BOLIMLARI[i + 1].kalit
        : null,
  };
}
