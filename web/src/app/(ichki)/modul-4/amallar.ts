"use server";

import { revalidatePath } from "next/cache";

import {
  radarSora,
  sozlamaOchir,
  sozlamaYoz,
  yashirinOchir,
  yashirinQosh,
} from "@/lib/radar-baza";
import { sonniOqi, sozlamaKalitmi, sozlamaTekshir, symbolNormalla, yashirishGacha } from "@/lib/radar";
import { kirim } from "@/lib/session";

/** Modul 4.0.0 server amallari — FAQAT ADMIN.
 *
 * ADMINLIK HAR AMALDA QAYTA TEKSHIRILADI. Sahifadagi tekshiruv
 * yetarli emas: server amali ALOHIDA so'rov bo'lib keladi va uni
 * sahifani ochmasdan to'g'ridan-to'g'ri chaqirish mumkin
 * (`kuzatuv/amallar.ts` bilan bir xil qoida). Admin bo'lmasa amal
 * jimgina hech narsa qilmaydi.
 *
 * Kiritilgan qiymat `radar.ts` dagi sof tekshiruvlardan o'tadi —
 * rad etilgan qiymat bazaga UMUMAN tushmaydi. Hisob botda qoladi:
 * sayt faqat bayroq, chegara va yashirin ro'yxatni yozadi.
 */

/** "Hozir tekshir" — botga qo'lda tekshiruv buyrug'i qoldiriladi. */
export async function radarniSora(): Promise<void> {
  const { admin } = await kirim();
  if (!admin) return;
  radarSora();
  revalidatePath("/modul-4");
}

/** Chegarani saqlash. Keyingi sessiyadan kuchga kiradi. */
export async function sozlamaSaqla(forma: FormData): Promise<void> {
  const { admin, foydalanuvchi } = await kirim();
  if (!admin) return;
  const tekshiruv = sozlamaTekshir(String(forma.get("kalit") ?? ""), sonniOqi(forma.get("qiymat")));
  if (!tekshiruv.ok) return;
  // Admin hali botga /start bermagan bo'lsa bazada yo'q — `null`.
  sozlamaYoz(tekshiruv.kalit, tekshiruv.qiymat, foydalanuvchi?.telegramId ?? null);
  revalidatePath("/modul-4");
}

/** "Standartga qaytarish" — admin qiymati o'chadi, YAML dagisi qaytadi. */
export async function sozlamaTikla(forma: FormData): Promise<void> {
  const { admin } = await kirim();
  if (!admin) return;
  const kalit = String(forma.get("kalit") ?? "");
  if (!sozlamaKalitmi(kalit)) return;
  sozlamaOchir(kalit);
  revalidatePath("/modul-4");
}

/** Coinni yashirish: 1 / 7 / 30 kun yoki doimiy. */
export async function coinYashir(forma: FormData): Promise<void> {
  const { admin, foydalanuvchi } = await kirim();
  if (!admin) return;
  const symbol = symbolNormalla(forma.get("symbol"));
  const gacha = yashirishGacha(forma.get("muddat"), new Date());
  if (!symbol || gacha === undefined) return;
  // Sabab — erkin matn, lekin chegarali: bazaga roman yozilmasin.
  const sabab = String(forma.get("sabab") ?? "").trim().slice(0, 300);
  yashirinQosh(symbol, sabab, gacha, foydalanuvchi?.telegramId ?? null);
  revalidatePath("/modul-4");
}

/** Yashirishni bekor qilish. */
export async function coinOch(forma: FormData): Promise<void> {
  const { admin } = await kirim();
  if (!admin) return;
  // Ro'yxatdagi symbol aynan bazadagidek keladi. Normallashtirib
  // bo'lmaydigan eski yozuv ham o'chira olinsin — lekin faqat oddiy
  // belgilar bilan (parametr bo'lib uzatiladi, baribir xavfsiz).
  const xom = String(forma.get("symbol") ?? "").trim();
  const symbol = symbolNormalla(xom) ?? (/^[A-Z0-9]{1,32}$/.test(xom) ? xom : null);
  if (!symbol) return;
  yashirinOchir(symbol);
  revalidatePath("/modul-4");
}
