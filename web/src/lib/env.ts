/** Muhit o'zgaruvchilari — bitta joyda, aniq xato xabarlari bilan.
 *
 * Nima uchun `process.env` ni to'g'ridan-to'g'ri o'qimaymiz: yetishmayotgan
 * o'zgaruvchi `undefined` bo'lib o'tib ketadi va xato ancha keyin, boshqa
 * joyda chiqadi. Masalan `BOT_TOKEN` bo'lmasa HMAC tekshiruvi jimgina
 * HAMMA kirishni rad etadi — bu "sayt buzuq" kabi ko'rinadi, sababi esa
 * ko'rinmaydi.
 */

class EnvError extends Error {}

function talab(nom: string): string {
  const qiymat = process.env[nom]?.trim();
  if (!qiymat) {
    throw new EnvError(
      `${nom} o'rnatilmagan. Railway'da (yoki .env.local faylida) shu ` +
        `o'zgaruvchini qo'shing — web/README.md ga qarang.`,
    );
  }
  return qiymat;
}

/** SQLAlchemy manzilidan fayl yo'lini ajratadi.
 *
 * SQLAlchemy qoidasi (uch va TO'RT qiyshiq chiziq farq qiladi):
 *   sqlite:///data/hcs.db    -> `data/hcs.db`   (NISBIY yo'l)
 *   sqlite:////data/hcs.db   -> `/data/hcs.db`  (MUTLAQ yo'l)
 *
 * Ya'ni sxemadan keyin qolgan qismdan ATIGI BITTA qiyshiq chiziq
 * olib tashlanadi. Bot Railway'da to'rt chiziqli variantni ishlatadi
 * (`bot/hosting.py`), mahalliy ishlashda esa uch chiziqli.
 *
 * Bot va sayt BIR XIL faylni ishlatadi, shuning uchun manzil ham bir
 * xil o'zgaruvchidan (`DATABASE_URL`) olinadi.
 */
export function sqliteYoli(url: string | undefined): string {
  const xom = url?.trim();
  if (!xom) return "data/hcs.db";
  if (!xom.startsWith("sqlite")) {
    throw new EnvError(
      `DATABASE_URL SQLite emas (${xom.split(":")[0]}). Sayt hozircha faqat ` +
        `SQLite bilan ishlaydi — Postgres'ga o'tilsa src/lib/db.ts qayta yoziladi.`,
    );
  }
  const keyin = xom.replace(/^sqlite(\+\w+)?:\/\//, "");
  return keyin.startsWith("/") ? keyin.slice(1) : keyin;
}

function adminlar(xom: string | undefined): ReadonlySet<number> {
  if (!xom) return new Set();
  const ids = xom
    .replace(/;/g, ",")
    .split(",")
    .map((q) => q.trim())
    .filter(Boolean)
    .map((q) => {
      const n = Number(q);
      if (!Number.isInteger(n))
        throw new EnvError(`ADMIN_IDS noto'g'ri qiymat: ${q}`);
      return n;
    });
  return new Set(ids);
}

/** Sozlamalar HAR SO'ROVDA o'qiladi, modul yuklanganda emas.
 *
 * Nima uchun: Next.js sahifalarni yig'ish (build) paytida ham ishga
 * tushiradi. Modul darajasida `talab("BOT_TOKEN")` chaqirilsa, build
 * mashinasida token yo'qligi uchun butun yig'ish yiqiladi — holbuki token
 * faqat ishlash paytida kerak.
 */
export function env() {
  return {
    botToken: talab("BOT_TOKEN"),
    /** Telegram Login Widget uchun — `@` siz, masalan `hcs_academya` */
    botUsername: talab("BOT_USERNAME").replace(/^@/, ""),
    dbPath: bazaYoli(),
    adminIds: adminlar(process.env.ADMIN_IDS),
  };
}

/** Baza yo'li ALOHIDA funksiya, `env()` ning ichida emas.
 *
 * Nima uchun: `env()` `BOT_TOKEN` ni talab qiladi, baza esa tokendan
 * mutlaqo mustaqil. Bittasiga bog'lasak, bazani o'qish uchun ham token
 * kerak bo'lib qoladi — bu testda ham, kelajakda token kerak bo'lmagan
 * har qanday joyda ham sun'iy to'siq. */
export function bazaYoli(): string {
  return sqliteYoli(process.env.DATABASE_URL);
}

/** Botga yo'naltirish havolasi — to'lov oqimi SAYTDA emas, botda. */
export function botHavolasi(botUsername: string, start = "pay"): string {
  return `https://t.me/${botUsername}?start=${start}`;
}

export { EnvError };
