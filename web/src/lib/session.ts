import { cookies } from "next/headers";

import { SESSIYA_COOKIE, sessiyaOqi } from "@/lib/auth";
import { env } from "@/lib/env";
import { STANDART_TIL, TIL_COOKIE, type Til, tilmi } from "@/lib/i18n";
import {
  type Foydalanuvchi,
  type Obuna,
  type Tarif,
  faolObuna,
  foydalanuvchiOl,
} from "@/lib/queries";

/** Har bir sahifa uchun "kim so'rayapti" konteksti.
 *
 * Muhim: admin ekanlik BAZADAN emas, muhit o'zgaruvchisidan (`ADMIN_IDS`)
 * aniqlanadi — botdagi bilan bir xil manba (1.1-band). Bazadagi `role`
 * ustuniga tayansak, bazaga yozish imkoni bo'lgan har kim o'zini admin
 * qilib qo'yishi mumkin bo'lardi.
 */
export type Kirim = {
  kirgan: boolean;
  foydalanuvchi: Foydalanuvchi | null;
  obuna: Obuna | null;
  tarif: Tarif | null;
  admin: boolean;
  til: Til;
};

export async function kirim(): Promise<Kirim> {
  const jar = await cookies();
  const til = tilOqi(jar.get(TIL_COOKIE)?.value);

  let telegramId: number | null = null;
  try {
    telegramId = sessiyaOqi(jar.get(SESSIYA_COOKIE)?.value, env().botToken);
  } catch {
    // BOT_TOKEN yo'q — sozlama xatosi. Sahifa "kirilmagan" holatda
    // ko'rsatiladi, sabab esa /kirish sahifasida yoziladi.
    telegramId = null;
  }

  if (telegramId === null) {
    return {
      kirgan: false,
      foydalanuvchi: null,
      obuna: null,
      tarif: null,
      admin: false,
      til,
    };
  }

  const foydalanuvchi = foydalanuvchiOl(telegramId);
  const admin = env().adminIds.has(telegramId);

  // Bazada yo'q, lekin ADMIN_IDS da bor — admin hali botga /start
  // bermagan holat. Panelga kirishi kerak, aks holda "tovuqmi-tuxummi"
  // vaziyati chiqadi.
  if (!foydalanuvchi) {
    return {
      kirgan: admin,
      foydalanuvchi: null,
      obuna: null,
      tarif: null,
      admin,
      til,
    };
  }

  const obuna = faolObuna(foydalanuvchi.id);
  return {
    kirgan: true,
    foydalanuvchi,
    obuna,
    // Admin barcha bo'limlarni ko'radi — botdagi bilan bir xil xatti-harakat
    tarif: admin ? "premium" : (obuna?.tier ?? null),
    admin,
    til,
  };
}

export function tilOqi(xom: string | undefined): Til {
  return tilmi(xom) ? xom : STANDART_TIL;
}
