import ru from "./ru.json" with { type: "json" };
import uz from "./uz.json" with { type: "json" };

/** Ko'p tillilik — matnlar kodga QATTIQ YOZILMAYDI.
 *
 * Botdagi `bot/i18n/` bilan bir xil yondashuv: JSON fayllar, nuqtali
 * kalitlar. Yangi til qo'shish — yangi JSON fayl va shu yerdagi
 * `TILLAR` ga bitta qator.
 */

export const TILLAR = { uz, ru } as const;
export type Til = keyof typeof TILLAR;
export const STANDART_TIL: Til = "uz";
export const TIL_COOKIE = "hcs_til";

export const TIL_NOMLARI: Record<Til, string> = {
  uz: "O'zbekcha",
  ru: "Русский",
};

export function tilmi(x: string | undefined | null): x is Til {
  return x === "uz" || x === "ru";
}

type Lugat = Record<string, unknown>;

/** Nuqtali kalit bo'yicha matn: `t("menyu.signallar")`.
 *
 * Kalit topilmasa KALITNING O'ZI qaytariladi, xato tashlanmaydi. Nima
 * uchun: bitta yetishmayotgan matn butun sahifani yiqitmasligi kerak —
 * ekranda `menyu.signallar` ko'rinsa, muammo darhol ko'zga tashlanadi
 * va tuzatiladi.
 */
export function tarjima(til: Til, kalit: string): string {
  const yur = (lugat: Lugat): string | null => {
    let joriy: unknown = lugat;
    for (const qism of kalit.split(".")) {
      if (typeof joriy !== "object" || joriy === null) return null;
      joriy = (joriy as Lugat)[qism];
    }
    return typeof joriy === "string" ? joriy : null;
  };
  return yur(TILLAR[til] as Lugat) ?? yur(TILLAR[STANDART_TIL] as Lugat) ?? kalit;
}

/** Sahifada qulay ishlatish uchun: `const t = tarjimon(til)` */
export function tarjimon(til: Til) {
  return (kalit: string) => tarjima(til, kalit);
}

/** Kalkulyator va grafik matnlari — BITTA joyda.
 *
 * Bu ro'yxat ikki sahifada kerak: signallar ro'yxatida va signal
 * sahifasida. Ikki nusxa qilinsa, yangi kalit qo'shilganda biri
 * yangilanib ikkinchisi qolib ketardi — bu loyihada allaqachon
 * uchragan xato turi.
 */
export function kalkulyatorMatnlari(t: (kalit: string) => string) {
  return {
    ochish: t("signal.ochish"),
    himoya: t("signal.himoya"),
    grafik_xato: t("signal.grafik_xato"),
    sarlavha: t("signal.kalk_sarlavha"),
    summa: t("signal.kalk_summa"),
    kirish: t("signal.kalk_kirish"),
    stop: t("signal.kalk_stop"),
    ulush: t("signal.kalk_ulush"),
    umumiy: t("signal.kalk_umumiy"),
    stop_agar: t("signal.kalk_stop_agar"),
    jami: t("signal.kalk_jami"),
    ulush_xato: t("signal.kalk_ulush_xato"),
    ogohlantirish: t("signal.kalk_ogohlantirish"),
  };
}
