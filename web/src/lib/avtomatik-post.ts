import { db, songaAylantir, vaqtSatri } from "./db.ts";
import { avtomatikPost, YOPIQ_HOLATLAR } from "./queries.ts";

/** Signal va haftalik hisobot uchun AVTOMATIK postlar.
 *
 * NEGA ALOHIDA FAYL. Dars posti darsni saqlash oqimida yoziladi —
 * o'sha yerda "yangi dars qo'shildi" degan aniq nuqta bor. Signal
 * uchun bunday nuqta YO'Q: signalni ham sayt (`signalYarat`), ham bot
 * (`core/services/`, Python) yozadi. Ikkala yo'lga ham chaqiruv
 * qo'ysak, TypeScript va Python da bir xil mantiqning ikki nusxasi
 * paydo bo'lardi va vaqt o'tib ular bir-biridan farq qila boshlardi.
 *
 * Shuning uchun bu yerda boshqa yo'l tanlandi: post YOZUVCHIDAN emas,
 * BAZANING O'ZIDAN olinadi. "Tarqatilgan, lekin posti yo'q signal
 * bormi?" degan savolga javob signal qaysi tilda yozilganiga
 * bog'liq emas.
 *
 * QACHON ISHLAYDI. Bosh sahifa ochilganda. Postlar faqat bosh
 * sahifada ko'rinadi, ya'ni ular hech kim qaramayotgan paytda
 * yozilishi shart emas. Buning uchun alohida fon vazifasi (cron)
 * qurilmadi — u yana bitta ishlab turishi kerak bo'lgan qism
 * bo'lardi.
 *
 * TAKRORLANMASLIK KAFOLATI baza tomonida: `uq_post_manba` unique
 * indeksi (`source_kind` + `source_id`). Ikki foydalanuvchi bir
 * vaqtda bosh sahifani ochsa ham, ikkinchi yozuv jimgina tushib
 * qoladi.
 */

// --------------------------------------------------------------------------- //
//  Sof yordamchilar (bazasiz — test qilinadi)
// --------------------------------------------------------------------------- //

/** ISO 8601 hafta raqami (dushanbadan boshlanadi, UTC bo'yicha).
 *
 * `getUTC*` ATAYLAB: server qaysi zonada turgani natijaga ta'sir
 * qilmasin. Bazadagi vaqtlar ham UTC.
 */
export function isoHafta(d: Date): { yil: number; hafta: number } {
  const t = new Date(
    Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()),
  );
  // ISO qoidasi: hafta qaysi YILGA tegishli ekanini o'sha haftaning
  // PAYSHANBASI hal qiladi. Shuning uchun avval payshanbaga ko'chamiz.
  const kun = t.getUTCDay() || 7; // yakshanba 0 -> 7
  t.setUTCDate(t.getUTCDate() + 4 - kun);
  const yil = t.getUTCFullYear();
  const yilBoshi = Date.UTC(yil, 0, 1);
  const hafta = Math.ceil(((t.getTime() - yilBoshi) / 86400000 + 1) / 7);
  return { yil, hafta };
}

/** Shu sana tushgan haftaning dushanbasi, 00:00 UTC. */
export function haftaBoshi(d: Date): Date {
  const t = new Date(
    Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()),
  );
  const kun = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() - (kun - 1));
  return t;
}

const KUN = 86400000;

/** Oxirgi TUGAGAN hafta: boshi, oxiri va raqami.
 *
 * Nima uchun "hozir minus 7 kun": bugun haftaning qaysi kuni
 * bo'lishidan qat'i nazar, undan bir hafta oldingi sana albatta
 * o'tgan (to'liq tugagan) haftaga tushadi. Joriy hafta hisobga
 * OLINMAYDI — u hali tugamagan, hisoboti ham to'liq bo'lmaydi.
 */
export function otganHafta(hozir: Date): {
  yil: number;
  hafta: number;
  boshi: Date;
  oxiri: Date;
} {
  const boshi = haftaBoshi(new Date(hozir.getTime() - 7 * KUN));
  const oxiri = new Date(boshi.getTime() + 7 * KUN);
  return { ...isoHafta(boshi), boshi, oxiri };
}

/** Hafta uchun `source_id`. Bitta hafta — bitta hisobot posti.
 *
 * `2026` + `36` -> `202636`. Raqam bo'lishi shart, chunki
 * `homepage_posts.source_id` — butun son ustuni. */
export function haftaKodi(yil: number, hafta: number): number {
  return yil * 100 + hafta;
}

export type HaftaNatijasi = {
  jami: number;
  tp2: number;
  tp1Keyin: number;
  stop: number;
  bekor: number;
  /** O'rtacha natija foizi — `null` bo'lsa hech bir signalda o'lchov yo'q */
  ortacha: number | null;
  /** O'rtacha nechta signaldan hisoblangani — raqamning og'irligi */
  ortachaSoni: number;
};

/** Haftalik hisobot MATNI — sof funksiya, shuning uchun test qilinadi.
 *
 * MATN BAZAGA YOZILADI, ya'ni bir marta va bitta tilda. Sayt ikki
 * tilli, lekin postning tarjimasi yo'q: post — "o'sha kuni yozilgan
 * xabar", tarjima qilinadigan interfeys emas. Botdagi kanal postlari
 * ham shunday ishlaydi.
 *
 * RAQAMLAR FAQAT O'LCHANGANI. "G'alaba foizi" yoki "kutilgan foyda"
 * kabi yig'ma ko'rsatkichlar bu yerda ATAYLAB yo'q: ular kam
 * namunada aldaydi (bir hafta = bir necha signal). Bu yerda faqat
 * sanoq turadi.
 */
export function hisobotMatni(
  yil: number,
  hafta: number,
  n: HaftaNatijasi,
): string {
  const qatorlar = [
    `${yil}-yil, ${hafta}-hafta yakuni`,
    "",
    `Yopilgan signallar: ${n.jami}`,
    `Nishonga yetdi (TP2): ${n.tp2}`,
    `TP1 dan keyin stop: ${n.tp1Keyin}`,
    `Stop: ${n.stop}`,
  ];
  if (n.bekor > 0) qatorlar.push(`Bekor qilindi: ${n.bekor}`);
  if (n.ortacha !== null) {
    const belgi = n.ortacha >= 0 ? "+" : "";
    qatorlar.push(
      `O'rtacha natija: ${belgi}${n.ortacha.toFixed(2)}% (${n.ortachaSoni} ta signaldan)`,
    );
  }
  return qatorlar.join("\n");
}

// --------------------------------------------------------------------------- //
//  Bazaga tegadigan qism
// --------------------------------------------------------------------------- //

/** Signal tarqatilgandan keyin shuncha kun ichida post yoziladi.
 *
 * NEGA OYNA BOR. Bu qoida yoqilgan kunda bazada allaqachon o'nlab
 * eski signal turibdi. Oynasiz birinchi ochilishda oqim o'sha
 * eskilar bilan to'lib ketardi.
 *
 * Oynadan chiqib ketgan signal posti YOZILMAYDI va bu yo'qotish
 * emas: post — "hozir yangi signal bor" degan xabar, uch kundan
 * keyin uning ma'nosi qolmaydi.
 */
const SIGNAL_OYNASI_KUN = 3;

/** Bir ochilishda ko'pi bilan shuncha signal posti. Kutilmagan holatda
 *  (masalan import qilingan tarix) oqim to'lib ketmasin. */
const BIR_MARTALIK_CHEGARA = 5;

/** Tarqatilgan, lekin posti yo'q signallar uchun post yozadi.
 *
 * FAQAT TARQATILGANI (`broadcast_at` to'la). Sabab: signal avval
 * OBUNACHILARGA boradi. Tarqatilmasidan oldin bosh sahifada e'lon
 * qilsak, pul to'lamagan odam to'lagandan oldin bilib olardi.
 *
 * POST MATNIDA COIN NOMI YO'Q — ATAYLAB. Dars uchun sarlavha
 * "sotiladigan qiymat": nomni bilgan odam darsni ko'rmaydi. Signal
 * boshqacha: bu spot, faqat sotib olish. "Hozir BTC" — signalning
 * O'ZI, tafsilotisiz ham ishlatib bo'ladi. Shuning uchun ochiq
 * oqimda faqat "signal bor" deyiladi, qolgani qulf ortida.
 *
 * Qaytadi: nechta yangi post yozilgani.
 */
export function signalPostlari(hozir = new Date()): number {
  const chegara = vaqtSatri(
    new Date(hozir.getTime() - SIGNAL_OYNASI_KUN * KUN),
  );
  const qatorlar = db()
    .prepare(
      `select s.id
         from signals s
         left join homepage_posts p
           on p.source_kind = 'signal' and p.source_id = s.id
        where s.broadcast_at is not null
          and s.broadcast_at >= ?
          and p.id is null
        order by s.id
        limit ?`,
    )
    .all(chegara, BIR_MARTALIK_CHEGARA) as { id: unknown }[];

  let yozildi = 0;
  for (const q of qatorlar) {
    const id = songaAylantir(q.id);
    const natija = avtomatikPost(
      "signal",
      id,
      "Yangi signal e'lon qilindi. Tafsilotlari obunachilar uchun.",
      `/signallar/${id}`,
      hozir,
    );
    if (natija.yangi) yozildi += 1;
  }
  return yozildi;
}

/** O'tgan haftaning yakuni — bitta post.
 *
 * SIGNAL BO'LMAGAN HAFTA UCHUN POST YOZILMAYDI. "Bu hafta 0 ta
 * signal" degan xabar har hafta takrorlansa, oqim mazmunsiz
 * qatorlar bilan to'lardi. Signal yo'qligining sababi esa Bozor
 * holati sahifasida ("Nega signal yo'q?") allaqachon ko'rsatilgan.
 *
 * Qaytadi: yangi post yozildimi.
 */
export function haftalikHisobot(hozir = new Date()): boolean {
  const { yil, hafta, boshi, oxiri } = otganHafta(hozir);

  const qatorlar = db()
    .prepare(
      `select status, result_pct, tp1_reached
         from signals
        where closed_at >= ? and closed_at < ?
          and status in (${YOPIQ_HOLATLAR.map(() => "?").join(", ")})`,
    )
    .all(vaqtSatri(boshi), vaqtSatri(oxiri), ...YOPIQ_HOLATLAR) as {
    status: string;
    result_pct: unknown;
    tp1_reached: unknown;
  }[];

  if (qatorlar.length === 0) return false;

  const natija: HaftaNatijasi = {
    jami: qatorlar.length,
    tp2: 0,
    tp1Keyin: 0,
    stop: 0,
    bekor: 0,
    ortacha: null,
    ortachaSoni: 0,
  };
  let yigindi = 0;
  for (const q of qatorlar) {
    if (q.status === "tp2_hit") natija.tp2 += 1;
    else if (q.status === "stopped") {
      if (q.tp1_reached) natija.tp1Keyin += 1;
      else natija.stop += 1;
    } else natija.bekor += 1; // `cancelled`, `timed_out`

    if (q.result_pct !== null && q.result_pct !== undefined) {
      yigindi += Number(q.result_pct);
      natija.ortachaSoni += 1;
    }
  }
  if (natija.ortachaSoni > 0) natija.ortacha = yigindi / natija.ortachaSoni;

  return avtomatikPost(
    "hisobot",
    haftaKodi(yil, hafta),
    hisobotMatni(yil, hafta, natija),
    "/statistika",
    hozir,
  ).yangi;
}

/** Bosh sahifa ochilganda chaqiriladi.
 *
 * HECH QACHON XATO OTMAYDI. Bu yordamchi ish: agar u yiqilsa, bosh
 * sahifaning O'ZI ochilmay qolardi. Post yozilmagani — kichik
 * yo'qotish, sahifaning ochilmagani — katta.
 */
export function avtomatikPostlarniYangila(hozir = new Date()): {
  signal: number;
  hisobot: boolean;
} {
  let signal = 0;
  let hisobot = false;
  try {
    signal = signalPostlari(hozir);
  } catch {
    signal = 0;
  }
  try {
    hisobot = haftalikHisobot(hozir);
  } catch {
    hisobot = false;
  }
  return { signal, hisobot };
}
