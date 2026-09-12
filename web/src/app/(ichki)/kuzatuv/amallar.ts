"use server";

import { revalidatePath } from "next/cache";

import { kuzatuvSkaniSora } from "@/lib/queries";
import { kirim } from "@/lib/session";

/** Admin "hozir yangila" bosdi — botga BUYRUQ qoldiriladi.
 *
 * ADMINLIK QAYTA TEKSHIRILADI. Layout dagi tekshiruv yetarli emas:
 * server amali ALOHIDA so'rov bo'lib keladi va layout u uchun
 * yugurmaydi (`admin/amallar.ts` dagi bilan bir xil qoida).
 *
 * Sayt skanni O'ZI bajarmaydi — u faqat bayroq qo'yadi. Hisob
 * botda, `core/watch_panel/coin_scanner.py` da qoladi.
 */
export async function skanniSora(): Promise<void> {
  const { admin } = await kirim();
  if (!admin) return;
  kuzatuvSkaniSora();
  revalidatePath("/kuzatuv");
}
