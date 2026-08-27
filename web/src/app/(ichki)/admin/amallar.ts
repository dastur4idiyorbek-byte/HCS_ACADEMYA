"use server";

import { revalidatePath } from "next/cache";

import { env } from "@/lib/env";
import { tolovniRadEt, tolovniTasdiqla } from "@/lib/queries";
import { xabarYubor } from "@/lib/telegram";
import { kirim } from "@/lib/session";

/** Admin amallari — server tomonda.
 *
 * HAR BIR amalda adminlik QAYTA tekshiriladi. Sahifa yuklanganda
 * tekshirish yetarli emas: server amali (server action) alohida so'rov,
 * uni to'g'ridan-to'g'ri chaqirish mumkin.
 */
async function adminTekshir(): Promise<number> {
  const { admin, foydalanuvchi } = await kirim();
  if (!admin) throw new Error("Ruxsat yo'q");
  // Admin bazada bo'lmasligi mumkin (hali /start bermagan) — u holda
  // `reviewed_by` uchun 0 emas, haqiqiy Telegram ID kerak.
  return foydalanuvchi?.telegramId ?? 0;
}

export async function tasdiqla(forma: FormData): Promise<void> {
  const adminId = await adminTekshir();
  const id = Number(forma.get("id"));
  const natija = tolovniTasdiqla(id, adminId);

  if (natija.ok) {
    const sana = natija.expiresAt.toISOString().slice(0, 16).replace("T", " ");
    await xabarYubor(
      env().botToken,
      natija.telegramId,
      `✅ To'lovingiz tasdiqlandi. Obuna ${sana} (UTC) gacha amal qiladi.`,
    );
  }
  revalidatePath("/admin");
}

export async function radEt(forma: FormData): Promise<void> {
  const adminId = await adminTekshir();
  const id = Number(forma.get("id"));
  const sabab = String(forma.get("sabab") ?? "").trim() || "Sabab ko'rsatilmadi";
  const natija = tolovniRadEt(id, adminId, sabab);

  if (natija.ok) {
    await xabarYubor(
      env().botToken,
      natija.telegramId,
      `❌ To'lovingiz rad etildi.\nSabab: ${sabab}`,
    );
  }
  revalidatePath("/admin");
}
