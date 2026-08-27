"use server";

import { revalidatePath } from "next/cache";

import { env } from "@/lib/env";
import {
  type HalolHolat,
  type Tarif,
  coinQaroriniBelgila,
  coinQaroriniOchir,
  narxniYangila,
  tolovniRadEt,
  tolovniTasdiqla,
} from "@/lib/queries";
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


// --------------------------------------------------------------------------- //
//  Narxlar (1.2-band)
// --------------------------------------------------------------------------- //

export async function narxSaqla(forma: FormData): Promise<void> {
  await adminTekshir();

  // Foydalanuvchi "12 500" yoki "12,500" deb yozishi mumkin — bo'sh joy
  // va vergul olib tashlanadi. Boshqa har qanday belgi qolsa, `Number`
  // `NaN` beradi va `narxniYangila` uni rad etadi.
  const xom = String(forma.get("amount") ?? "").replace(/[\s,]/g, "");
  const rekvizit = String(forma.get("payment_details") ?? "").trim();

  narxniYangila(
    String(forma.get("tier")) as Tarif,
    String(forma.get("period")),
    String(forma.get("currency")),
    Number(xom),
    rekvizit || null,
  );
  revalidatePath("/admin/narxlar");
}

// --------------------------------------------------------------------------- //
//  Halol ro'yxat (1.4 / 3.4-band)
// --------------------------------------------------------------------------- //

export async function qarorSaqla(forma: FormData): Promise<void> {
  const adminId = await adminTekshir();
  coinQaroriniBelgila(
    String(forma.get("symbol") ?? ""),
    String(forma.get("status") ?? "") as HalolHolat,
    String(forma.get("reason") ?? ""),
    adminId,
  );
  revalidatePath("/admin/halol");
}

export async function qarorOchir(forma: FormData): Promise<void> {
  await adminTekshir();
  coinQaroriniOchir(String(forma.get("symbol") ?? ""));
  revalidatePath("/admin/halol");
}
