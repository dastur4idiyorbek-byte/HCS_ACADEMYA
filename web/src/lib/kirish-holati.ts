/** Signalga kirish holati — SOF funksiyalar, brauzerda ham ishlaydi.
 *
 * Ikki qoida shu yerda, chunki ular ikki joyda kerak (ro'yxat va
 * signal sahifasi) va ikkalasi bir xil javob berishi shart. Bitta
 * qoida ikki joyda yozilsa, biri o'zgarib ikkinchisi qolib ketardi —
 * loyihaning 1-naqshi.
 */

/** AMALDAGI Stop — TP1 olingach kirish narxiga ko'tariladi.
 *
 * Bu `core/domain/models.py: Signal.effective_stop` ning aynan aksi.
 * Botda Stop shu darajada kuzatiladi, saytda esa kartochka, grafik va
 * kalkulyator shu raqamni ko'rsatishi kerak — aks holda foydalanuvchi
 * bazadagi eski Stopga qarab pozitsiya hisoblab, tizim kuzatayotgan
 * darajadan boshqa joyga Stop qo'yardi.
 */
export function amaldagiStop(
  entry: number,
  stop: number,
  tp1Olindi: boolean,
): number {
  return tp1Olindi ? entry : stop;
}

/** Kirish nuqtasidan narx qanchalik uzoqlashgan (mutlaq foiz). */
export function uzoqlashish(entry: number, hozir: number): number | null {
  if (!Number.isFinite(entry) || !Number.isFinite(hozir) || entry <= 0)
    return null;
  return Math.abs((hozir - entry) / entry) * 100;
}

/** Signal hali KUTILMOQDAMI — narx kirish nuqtasiga yetmagan.
 *
 * `pending` — limit buyurtma joyiga qo'yilgan, narx hali unga
 * tushmagan. Bu holat MUAMMO EMAS, u REJANING O'ZI: signal aynan
 * shu narxga tushishini kutish uchun berilgan.
 *
 * Alohida funksiya bo'lishining sababi: bu qoida ikki joyda kerak
 * (ro'yxat va signal sahifasi) va ikkalasi bir xil javob berishi
 * shart.
 */
export function kutilmoqdami(holat: string): boolean {
  return holat === "pending";
}

/** Hozir kirish xavflimi — YANGI foydalanuvchi uchun.
 *
 * IKKALA TOMONGA ham qaraladi. Yuqoriga ketgan bo'lsa TP gacha masofa
 * qisqargan va Stopgacha uzoqlashgan; pastga ketgan bo'lsa Stop
 * yaqinlashgan. Ikkalasida ham kirish signal berilgan paytdagidan
 * yomonroq — nisbat o'sha nisbat emas.
 *
 * LEKIN FAQAT NARX KIRISH NUQTASIGA YETGANDAN KEYIN.
 *
 * Nima uchun bu shart qo'shildi. Ilgari qoida faqat masofaga
 * qarardi va `Math.abs` ikkala tomonni bir xil ko'rardi. Natijada
 * limit signal HALI KUTAYOTGAN paytda — narx entry'dan 3-4% yuqorida
 * turganda — sayt "bu signalga hozir kelish tavsiya etilmaydi,
 * xavf oshgan" deb yozardi.
 *
 * Bu chalg'ituvchi edi va aslida TESKARI ma'no berardi: o'sha
 * masofa signalning KAMCHILIGI emas, uning REJASI. Narx hali
 * kirish nuqtasiga tushmagan, ya'ni hech qanday xavf yo'q —
 * kutilmoqda.
 *
 * Ogohlantirish o'z ma'nosini faqat narx entry'ga YETGANDAN keyin
 * topadi: o'shanda undan yuqoriga chiqish TP masofasini qisqartiradi,
 * pastga tushish esa Stopni yaqinlashtiradi.
 *
 * Narx noma'lum bo'lsa `false`: yolg'on ogohlantirish ham, yolg'on
 * xotirjamlik ham bermaymiz.
 */
export function kechQoldimi(
  entry: number,
  hozir: number | null,
  chegaraFoiz: number,
  holat: string,
): boolean {
  if (hozir === null) return false;
  if (kutilmoqdami(holat)) return false;
  const masofa = uzoqlashish(entry, hozir);
  return masofa !== null && masofa >= chegaraFoiz;
}
