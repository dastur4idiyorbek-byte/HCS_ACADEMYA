import { createHash, createHmac, timingSafeEqual } from "node:crypto";

/** Telegram orqali kirish — tekshiruv va sessiya.
 *
 * XAVFSIZLIK: Telegram Login Widget ma'lumotni BRAUZER orqali qaytaradi.
 * Ya'ni uni istalgan odam qo'lda yasab yuborishi mumkin — "men admin
 * 123456 man" deb. Yagona himoya — `hash` maydonini bot tokeni bilan
 * qayta hisoblab solishtirish. Bu qadam MAJBURIY (topshiriq 2-bo'limi).
 */

export type TelegramLogin = {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
};

/** Telegram hujjatiga ko'ra 24 soatdan eski tasdiq qabul qilinmaydi. */
const MAX_AUTH_YOSHI_SEK = 86_400;

/** Sessiya muddati — topshiriq 2-bo'limi: 144 soat (6 kun). */
export const SESSIYA_SEK = 144 * 60 * 60;

export const SESSIYA_COOKIE = "hcs_session";

function xavfsizTeng(a: string, b: string): boolean {
  const ab = Buffer.from(a, "utf8");
  const bb = Buffer.from(b, "utf8");
  // Uzunlik farq qilsa `timingSafeEqual` xato beradi — avval tekshiramiz.
  // Uzunlikning o'zi sir emas, shuning uchun bu sizib chiqish emas.
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

/**
 * Widget qaytargan ma'lumotni tekshiradi.
 *
 * @returns tasdiqlangan ma'lumot, yoki `null` — soxta/eskirgan bo'lsa.
 *          Nima uchun `null`, xato emas: bu kutilgan holat (0.3-band
 *          fail-safe ruhi) — soxta so'rov tizimni yiqitmasligi kerak.
 */
export function telegramLoginTekshir(
  xom: Record<string, string>,
  botToken: string,
  hozir: Date = new Date(),
): TelegramLogin | null {
  const { hash, ...maydonlar } = xom;
  if (!hash) return null;

  // Telegram algoritmi: kalitlar alifbo tartibida "kalit=qiymat" bo'lib,
  // "\n" bilan birlashtiriladi; kalit esa SHA256(bot_token).
  const tekshiruvSatri = Object.keys(maydonlar)
    .sort()
    .map((k) => `${k}=${maydonlar[k]}`)
    .join("\n");

  const sirKalit = createHash("sha256").update(botToken).digest();
  const kutilgan = createHmac("sha256", sirKalit).update(tekshiruvSatri).digest("hex");
  if (!xavfsizTeng(kutilgan, hash)) return null;

  const authDate = Number(maydonlar.auth_date);
  const id = Number(maydonlar.id);
  if (!Number.isInteger(id) || !Number.isInteger(authDate)) return null;

  // Eskirgan tasdiqni qayta ishlatishdan himoya (replay attack)
  const yosh = Math.floor(hozir.getTime() / 1000) - authDate;
  if (yosh < 0 || yosh > MAX_AUTH_YOSHI_SEK) return null;

  return {
    id,
    first_name: maydonlar.first_name,
    last_name: maydonlar.last_name,
    username: maydonlar.username,
    photo_url: maydonlar.photo_url,
    auth_date: authDate,
  };
}

// --------------------------------------------------------------------------- //
//  Sessiya tokeni
// --------------------------------------------------------------------------- //

/** Sessiya kaliti bot tokenidan HOSIL QILINADI, to'g'ridan-to'g'ri
 *  ishlatilmaydi: bitta sir ikki xil vazifada ishlatilsa, biridagi
 *  kamchilik ikkinchisiga o'tadi. Qo'shimcha muhit o'zgaruvchisi ham
 *  kerak emas — ya'ni uni "keyin qo'shaman" deb unutib bo'lmaydi. */
function sessiyaKaliti(botToken: string): Buffer {
  return createHmac("sha256", botToken).update("hcs-web-session-v1").digest();
}

type Yuk = { tid: number; exp: number };

function b64url(b: Buffer): string {
  return b.toString("base64url");
}

export function sessiyaYarat(
  telegramId: number,
  botToken: string,
  hozir: Date = new Date(),
): { token: string; expires: Date } {
  const exp = Math.floor(hozir.getTime() / 1000) + SESSIYA_SEK;
  const yuk: Yuk = { tid: telegramId, exp };
  const tana = b64url(Buffer.from(JSON.stringify(yuk), "utf8"));
  const imzo = b64url(createHmac("sha256", sessiyaKaliti(botToken)).update(tana).digest());
  return { token: `${tana}.${imzo}`, expires: new Date(exp * 1000) };
}

/** Tokenni tekshiradi. Buzilgan, imzosi noto'g'ri yoki muddati o'tgan
 *  bo'lsa — `null`. Chaqiruvchi uchun uchala holat bir xil: kirish yo'q. */
export function sessiyaOqi(
  token: string | undefined,
  botToken: string,
  hozir: Date = new Date(),
): number | null {
  if (!token) return null;
  const [tana, imzo] = token.split(".");
  if (!tana || !imzo) return null;

  const kutilgan = b64url(createHmac("sha256", sessiyaKaliti(botToken)).update(tana).digest());
  if (!xavfsizTeng(kutilgan, imzo)) return null;

  try {
    const yuk = JSON.parse(Buffer.from(tana, "base64url").toString("utf8")) as Yuk;
    if (typeof yuk.tid !== "number" || typeof yuk.exp !== "number") return null;
    if (yuk.exp * 1000 <= hozir.getTime()) return null;
    return yuk.tid;
  } catch {
    return null;
  }
}
