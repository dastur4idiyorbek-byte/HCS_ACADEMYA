/** Signal grafiklarini kartochkaga uzatiladigan ko'rinishga aylantiradi.
 *
 * BITTA JOYDA: bu ro'yxat sahifasida ham, alohida signal sahifasida
 * ham kerak. Ikki joyda yozilsa, biri o'zgarib ikkinchisi qolib
 * ketardi — loyihaning eng ko'p uchragan xatosi.
 *
 * Manzil `/api/signal-media/<nom>` — o'sha yo'l OBUNANI tekshiradi.
 * Rasm signalning bir qismi: unda kirish, Stop va TP darajalari
 * chizilgan bo'lishi mumkin.
 */
export type SignalRasmi = { manzil: string; izoh: string };

export function signalRasmlari(
  signal: { entryChartImage: string | null; resultChartImage: string | null },
  t: (kalit: string) => string,
): SignalRasmi[] {
  const natija: SignalRasmi[] = [];
  if (signal.entryChartImage) {
    natija.push({
      manzil: `/api/signal-media/${signal.entryChartImage}`,
      izoh: t("signal.rasm_kirish"),
    });
  }
  if (signal.resultChartImage) {
    natija.push({
      manzil: `/api/signal-media/${signal.resultChartImage}`,
      izoh: t("signal.rasm_natija"),
    });
  }
  return natija;
}
