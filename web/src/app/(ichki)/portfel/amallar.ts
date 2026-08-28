"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { balansSaqla } from "@/lib/queries";
import { kirim } from "@/lib/session";

/** Balansni saqlash — foydalanuvchining O'ZI uchun.
 *
 * `userId` FORMADAN OLINMAYDI, sessiyadan olinadi. Aks holda kimdir
 * boshqa odamning raqamini yuborib, uning balansini o'zgartira olardi.
 */
export async function balansSaqlash(forma: FormData): Promise<void> {
  const { foydalanuvchi } = await kirim();
  if (!foydalanuvchi) redirect("/kirish");

  const xom = String(forma.get("balans") ?? "").trim();
  // Bo'sh maydon — "ko'rsatmayman" degani, nol emas.
  const summa = xom === "" ? null : Number(xom.replace(/\s/g, "").replace(",", "."));
  const natija = balansSaqla(foydalanuvchi.id, summa);

  revalidatePath("/portfel");
  // Signal kartochkasidagi "Miqdor" ham shu balansdan hisoblanadi.
  revalidatePath("/signallar");
  redirect(natija.ok ? "/portfel" : `/portfel?xato=${encodeURIComponent(natija.sabab)}`);
}
