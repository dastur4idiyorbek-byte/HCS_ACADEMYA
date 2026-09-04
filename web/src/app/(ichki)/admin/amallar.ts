"use server";

import { unlink } from "node:fs/promises";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { env } from "@/lib/env";
import { postYoli, signalRasmYoli } from "@/lib/media";
import {
  boshPostOchirish,
  boshPostQoshish,
  coinQaroriniBelgila,
  coinQaroriniOchir,
  darsOchir,
  darsSaqla,
  havolaOchir,
  havolaSaqla,
  narxniYangila,
  signalGrafigiBiriktir,
  signalOchir,
  signalYarat,
  tolovniRadEt,
  tolovniTasdiqla,
  type HalolHolat,
  type Tarif,
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
  const sabab =
    String(forma.get("sabab") ?? "").trim() || "Sabab ko'rsatilmadi";
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

// --------------------------------------------------------------------------- //
//  Qo'lda signal kiritish (2-bo'lim)
// --------------------------------------------------------------------------- //

/** Foydalanuvchi "1 234,56" yoki "1 234.56" deb yozishi mumkin. */
function narxOqi(xom: FormDataEntryValue | null): number {
  return Number(
    String(xom ?? "")
      .replace(/\s/g, "")
      .replace(",", "."),
  );
}

export async function signalBer(forma: FormData): Promise<void> {
  await adminTekshir();

  const natija = signalYarat({
    symbol: String(forma.get("symbol") ?? ""),
    entry: narxOqi(forma.get("entry")),
    stop: narxOqi(forma.get("stop")),
    tp1: narxOqi(forma.get("tp1")),
    tp2: narxOqi(forma.get("tp2")),
    note: String(forma.get("note") ?? "").trim() || null,
  });

  revalidatePath("/admin/signal");
  // Natija manzil orqali uzatiladi: sahifa signalni bazadan qayta o'qib,
  // ogohlantirishlarni o'zi hisoblaydi. Shunda ekrandagi matn har doim
  // SAQLANGAN signalga tegishli bo'ladi.
  redirect(
    natija.ok
      ? `/admin/signal?ok=${natija.id}`
      : `/admin/signal?xato=${encodeURIComponent(natija.sabab)}`,
  );
}

/** Signalni butunlay o'chirish — sinov yozuvlarini tozalash uchun.
 *
 * Signal statistikaga kiradi, shuning uchun sinov paytida yaratilgan
 * soxta signal g'alaba foizini va o'rtacha natijani buzadi. Uni
 * yashirish yetarli emas — hisob-kitobda qolaverardi.
 */
export async function signalOchirish(forma: FormData): Promise<void> {
  await adminTekshir();
  const id = Number(forma.get("id"));
  if (Number.isInteger(id) && id > 0) signalOchir(id);
  revalidatePath("/admin/signal");
  revalidatePath("/signallar");
  revalidatePath("/statistika");
  redirect("/admin/signal");
}

// --------------------------------------------------------------------------- //
//  Video darsliklar (1.5-band)
// --------------------------------------------------------------------------- //

export async function darsSaqlash(forma: FormData): Promise<void> {
  await adminTekshir();
  const xomId = String(forma.get("id") ?? "").trim();

  darsSaqla(xomId ? Number(xomId) : null, {
    title: String(forma.get("title") ?? ""),
    description: String(forma.get("description") ?? "").trim() || null,
    minTier: String(forma.get("min_tier") ?? "pro") as Tarif,
    position: Number(String(forma.get("position") ?? "0")) || 0,
    fileId: String(forma.get("file_id") ?? "").trim() || null,
    published: forma.get("published") === "on",
  });
  revalidatePath("/admin/darslar");
  revalidatePath("/video");
}

export async function darsOchirish(forma: FormData): Promise<void> {
  await adminTekshir();
  darsOchir(Number(forma.get("id")));
  revalidatePath("/admin/darslar");
  revalidatePath("/video");
}

// --------------------------------------------------------------------------- //
//  Ijtimoiy tarmoqlar
// --------------------------------------------------------------------------- //

export async function havolaSaqlash(forma: FormData): Promise<void> {
  await adminTekshir();
  const xomId = String(forma.get("id") ?? "").trim();

  havolaSaqla(xomId ? Number(xomId) : null, {
    title: String(forma.get("title") ?? ""),
    url: String(forma.get("url") ?? ""),
    icon: String(forma.get("icon") ?? "web"),
    position: Number(String(forma.get("position") ?? "0")) || 0,
    active: forma.get("active") === "on",
  });
  revalidatePath("/admin/havolalar");
  revalidatePath("/bosh");
}

export async function havolaOchirish(forma: FormData): Promise<void> {
  await adminTekshir();
  havolaOchir(Number(forma.get("id")));
  revalidatePath("/admin/havolalar");
  revalidatePath("/bosh");
}

// --------------------------------------------------------------------------- //
//  Bosh sahifa oqimi (4-prompt, 1-qism)
// --------------------------------------------------------------------------- //

export async function boshPostNashr(forma: FormData): Promise<void> {
  // `adminTekshir` Telegram ID qaytaradi, bu yerda esa BAZA id kerak
  // (`admin_id` — `users.id` ga havola), shuning uchun kirim bir marta
  // o'qiladi va ikkalasi undan olinadi.
  const { admin, foydalanuvchi } = await kirim();
  if (!admin) throw new Error("Ruxsat yo'q");

  const matn = String(forma.get("matn") ?? "");
  const media = String(forma.get("media") ?? "").trim() || null;

  const natija = boshPostQoshish(matn, media, foydalanuvchi?.id ?? null);
  if (!natija.ok) {
    redirect(
      `/admin/postlar?xato=${encodeURIComponent(natija.xato ?? "Xato")}`,
    );
  }
  revalidatePath("/admin/postlar");
  revalidatePath("/bosh");
}

export async function boshPostOchir(forma: FormData): Promise<void> {
  await adminTekshir();
  const natija = boshPostOchirish(Number(forma.get("id")));

  // Yozuv ketdi — fayl ham ketsin, aks holda disk asta-sekin to'lardi.
  // Fayl o'chmasa ham post yo'q: shuning uchun xato YUTILADI, lekin
  // amal to'xtamaydi.
  if (natija.media) {
    try {
      await unlink(postYoli(natija.media));
    } catch {
      // fayl allaqachon yo'q yoki nomi noto'g'ri — post baribir o'chdi
    }
  }
  revalidatePath("/admin/postlar");
  revalidatePath("/bosh");
}

// --------------------------------------------------------------------------- //
//  Signal grafiklari (4-prompt, 4-qism)
// --------------------------------------------------------------------------- //

export async function signalRasmiBiriktir(forma: FormData): Promise<void> {
  await adminTekshir();

  const id = Number(forma.get("id"));
  const xomMaydon = String(forma.get("maydon") ?? "");
  const maydon = xomMaydon === "natija" ? "natija" : "entry";
  // Bo'sh nom — "rasmni olib tashlash" degani.
  const nom = String(forma.get("nom") ?? "").trim() || null;

  const natija = signalGrafigiBiriktir(id, maydon, nom);
  if (!natija.ok) return;

  // Almashtirilgan rasm diskda abadiy qolmasin. Fayl o'chmasa ham
  // yozuv yangilangan, shuning uchun xato YUTILADI.
  if (natija.eskiNom) {
    try {
      await unlink(signalRasmYoli(natija.eskiNom));
    } catch {
      // fayl allaqachon yo'q yoki nomi noto'g'ri
    }
  }

  revalidatePath("/admin/signal");
  revalidatePath(`/signallar/${id}`);
  revalidatePath("/signallar");
}
