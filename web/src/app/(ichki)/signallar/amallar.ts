"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { pozitsiyaQayd } from "@/lib/queries";
import { kirim } from "@/lib/session";

/** "Men sotib oldim" — pozitsiyani qayd etish.
 *
 * `userId` SESSIYADAN olinadi, formadan emas: aks holda kimdir boshqa
 * odamning portfeliga yozuv qo'sha olardi. Kirish narxi ham formadan
 * emas, signal yozuvidan — o'ziga qulay narx yozib qo'yish yo'li
 * yopiladi.
 */
export async function kirdim(forma: FormData): Promise<void> {
  const { foydalanuvchi } = await kirim();
  if (!foydalanuvchi) redirect("/kirish");

  const signalId = Number(forma.get("signal_id"));
  const summa = Number(
    String(forma.get("summa") ?? "")
      .replace(/\s/g, "")
      .replace(",", "."),
  );
  const natija = pozitsiyaQayd(foydalanuvchi.id, signalId, summa);

  revalidatePath(`/signallar/${signalId}`);
  revalidatePath("/portfel");
  redirect(
    natija.ok
      ? `/signallar/${signalId}?kirdim=1`
      : `/signallar/${signalId}?xato=${encodeURIComponent(natija.sabab)}`,
  );
}
