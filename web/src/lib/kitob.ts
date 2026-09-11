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

/** Kitob tarkibi — sahifada ko'rsatiladigan bo'limlar. */
export const KITOB_BOLIMLARI = [
  { kalit: "asoslar", boblar: "1–7" },
  { kalit: "fundamental", boblar: "8–10" },
  { kalit: "texnik", boblar: "11–16" },
  { kalit: "smc", boblar: "17–18" },
  { kalit: "ict", boblar: "19–20" },
  { kalit: "risk", boblar: "21–23" },
] as const;
