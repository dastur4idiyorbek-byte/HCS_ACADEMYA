import { type Tarif, kirishMumkin, signallar, tarifQamraydi } from "@/lib/queries";

/** Sahifalar uchun kichik yordamchi hisoblar.
 *
 * Qoida: bu yerda ham biznes mantiq yo'q — faqat "nechta" kabi
 * ko'rsatkichlar. Signal berish/bermaslik qarori `core/` da qoladi.
 */
export function kirimMumkinSignallar(tarif: Tarif | null): { faol: number; jami: number } {
  // Obunasi yo'q odamga signallar soni ham ko'rsatilmaydi: 1.3-band
  // pullik bo'lim obunasizga ochilmasligini talab qiladi, son ham
  // ma'lumot — "bugun 3 ta signal bor" degani ham qiymatga ega.
  if (!tarifQamraydi(tarif, "lite")) return { faol: 0, jami: 0 };
  const royxat = signallar(200);
  return {
    faol: royxat.filter((s) => kirishMumkin(s.status)).length,
    jami: royxat.length,
  };
}
