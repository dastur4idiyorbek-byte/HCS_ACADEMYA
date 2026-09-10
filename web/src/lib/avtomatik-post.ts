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

/** Signal hodisasidan keyin shuncha kun ichida post yoziladi.
 *
 * NEGA OYNA BOR. Bu qoida yoqilgan kunda bazada allaqachon o'nlab
 * eski signal turibdi. Oynasiz birinchi ochilishda oqim o'sha
 * eskilar bilan to'lib ketardi.
 *
 * Oynadan chiqib ketgan signal posti YOZILMAYDI va bu yo'qotish
 * emas: post — "hozir shunday bo'ldi" degan xabar, uch kundan
 * keyin uning ma'nosi qolmaydi.
 */
const SIGNAL_OYNASI_KUN = 3;

/** Bir ochilishda ko'pi bilan shuncha signal posti. Kutilmagan holatda
 *  (masalan import qilingan tarix) oqim to'lib ketmasin. */
const BIR_MARTALIK_CHEGARA = 5;

/** Signalga aloqador post turlari — hammasi QULF ortida.
 *
 * Bosh sahifa shu ro'yxatga qarab qulf belgisini va "obuna bo'ling"
 * chaqirig'ini chizadi. Ro'yxat SHU YERDA turadi, chizuvchida emas:
 * yangi tur qo'shilib, chizuvchida unutilsa, qulflangan xabar ochiq
 * post kabi ko'rinardi.
 */
export const SIGNAL_MANBALARI = ["signal", "tp1", "tp2"] as const;
export type SignalManbasi = (typeof SIGNAL_MANBALARI)[number];

export function signalgaAloqador(manbaTuri: string): boolean {
  return (SIGNAL_MANBALARI as readonly string[]).includes(manbaTuri);
}

/** POST MATNIDA COIN NOMI YO'Q — ATAYLAB.
 *
 * Dars uchun sarlavha "sotiladigan qiymat": nomni bilgan odam darsni
 * ko'rmaydi. Signal boshqacha — bu spot, faqat sotib olish, ya'ni
 * "hozir BTC" degan gapning o'zi signalning MOHIYATI. Ochiq oqimda
 * faqat "shunday hodisa bo'ldi" deyiladi, qolgani qulf ortida.
 *
 * Matn bazaga bir marta yoziladi, ya'ni bitta tilda. Tugma va
 * "obuna bo'ling" chaqirig'i esa har bir foydalanuvchi uchun
 * ALOHIDA chiziladi — u tarjima qilinadi va obunachiga boshqacha
 * ko'rinadi.
 */
const MATNLAR: Record<SignalManbasi, string> = {
  signal: "Yangi signal keldi.",
  tp1: "Signal birinchi nishonga yetdi (TP1).",
  tp2: "Signal yakuniy nishonga yetdi (TP2).",
};

/** Signal posti yoziladigan bitta hodisa turi.
 *
 * `shart` — signals jadvalidagi qo'shimcha shart.
 * `hodisa` — `signal_events` dagi yozuv nomi (aniq VAQT shundan
 *   olinadi). `null` bo'lsa, tarqatish vaqti ishlatiladi.
 */
type Hodisa = {
  manba: SignalManbasi;
  shart: string;
  hodisa: string | null;
};

const HODISALAR: Hodisa[] = [
  // Tarqatilgan signal. FAQAT TARQATILGANI: signal avval
  // OBUNACHILARGA boradi. Tarqatilmasidan oldin bosh sahifada e'lon
  // qilsak, pul to'lamagan odam to'lagandan oldin bilib olardi.
  { manba: "signal", shart: "1 = 1", hodisa: null },
  // TP hodisalari. Ular ham faqat tarqatilgan signal uchun: hech kimga
  // yuborilmagan signalning natijasi bilan maqtanish ma'nosiz.
  { manba: "tp1", shart: "s.tp1_reached = 1", hodisa: "tp1_hit" },
  { manba: "tp2", shart: "s.status = 'tp2_hit'", hodisa: "tp2_hit" },
];

/** Hodisa qachon bo'lganini topadi.
 *
 * ANIQ VAQT `signal_events` da: `apply_event` har bir o'zgarishni
 * o'sha yerga yozadi va hodisa nomi holat qiymati bilan bir xil
 * (`tp1_hit`, `tp2_hit`).
 *
 * `signals.updated_at` ZAXIRA yo'l. U yolg'on chiqishi mumkin: TP1
 * dan keyin TP2 bo'lsa, `updated_at` ikkinchisiniki bo'ladi va TP1
 * "hozir bo'ldi" deb ko'rinardi. Shuning uchun u faqat audit izi
 * yo'q bo'lganda ishlatiladi.
 */
const HODISA_VAQTI = `
  coalesce(
    (select max(e.created_at) from signal_events e
      where e.signal_id = s.id and e.event = ?),
    s.updated_at)`;

/** Bitta hodisa turi bo'yicha yetishmayotgan postlarni yozadi.
 *
 * Qaytadi: nechta yangi post yozilgani.
 */
function hodisaPostlari(h: Hodisa, hozir: Date): number {
  const chegara = vaqtSatri(
    new Date(hozir.getTime() - SIGNAL_OYNASI_KUN * KUN),
  );
  const vaqtIfoda = h.hodisa === null ? "s.broadcast_at" : HODISA_VAQTI;
  // TARTIB SQL dagi `?` lar tartibi bilan bir xil bo'lishi SHART:
  // avval `p.source_kind`, keyin (bo'lsa) hodisa nomi, so'ng chegara
  // va limit. Aralashsa, so'rov xato bermaydi — jimgina noto'g'ri
  // javob qaytaradi.
  const parametrlar: (string | number)[] = [h.manba];
  if (h.hodisa !== null) parametrlar.push(h.hodisa);
  parametrlar.push(chegara, BIR_MARTALIK_CHEGARA);

  const qatorlar = db()
    .prepare(
      `select s.id from signals s
         left join homepage_posts p
           on p.source_kind = ? and p.source_id = s.id
        where s.broadcast_at is not null
          and p.id is null
          and ${h.shart}
          and ${vaqtIfoda} >= ?
        order by s.id
        limit ?`,
    )
    .all(...parametrlar) as { id: unknown }[];

  let yozildi = 0;
  for (const q of qatorlar) {
    const id = songaAylantir(q.id);
    const natija = avtomatikPost(
      h.manba,
      id,
      MATNLAR[h.manba],
      `/signallar/${id}`,
      hozir,
    );
    if (natija.yangi) yozildi += 1;
  }
  return yozildi;
}

/** Signal hodisalari uchun yetishmayotgan postlarni yozadi:
 *  yangi signal, TP1 va yakuniy nishon.
 *
 * Qaytadi: nechta yangi post yozilgani. */
export function signalPostlari(hozir = new Date()): number {
  let yozildi = 0;
  for (const h of HODISALAR) yozildi += hodisaPostlari(h, hozir);
  return yozildi;
}

// --------------------------------------------------------------------------- //
//  Dars va maqola
// --------------------------------------------------------------------------- //

/** Kontent turi -> post manbasi va tugma manzili.
 *
 * Video darslar bitta ro'yxat sahifasida turadi (`/video`), maqola
 * esa o'z sahifasiga ochiladi (`/bilimlar/{id}`) — shuning uchun
 * havola ham har xil.
 */
const KONTENT_TURLARI = {
  // Video darsi o'z sahifasiga emas, ro'yxatga ochiladi — shuning
  // uchun id ishlatilmaydi.
  video: { manba: "dars" as const, havola: () => "/video" },
  maqola: {
    manba: "maqola" as const,
    havola: (id: number) => `/bilimlar/${id}`,
  },
};

/** Chop etilgan, lekin posti yo'q dars va maqolalar uchun post yozadi.
 *
 * FAQAT CHOP ETILGANI (`is_published`). Chop etilmagan dars hali
 * tayyor emas — u haqda xabar berish erta bo'lardi.
 *
 * POST MATNI — SARLAVHANING O'ZI. Bu yerda coin nomi masalasi yo'q:
 * dars nomi "sotiladigan qiymat", ya'ni uni bilgan odam darsni
 * ko'rgan bo'lib qolmaydi. Qulflangan darsga olib boradigan tugma
 * ham YASHIRILMAYDI — bosilganda qulf ekrani chiqadi va odam nima
 * yetishmayotganini biladi.
 *
 * OYNA `created_at` BO'YICHA. Post — "yangi dars qo'shildi" degan
 * xabar. Dars uch kundan ko'proq oldin yaratilgan bo'lsa, u endi
 * yangi emas; `updated_at` ni olsak, eski darsning sarlavhasini
 * tuzatish uni oqimda "yangi" qilib ko'rsatardi.
 *
 * Qaytadi: nechta yangi post yozilgani.
 */
export function kontentPostlari(hozir = new Date()): number {
  const chegara = vaqtSatri(
    new Date(hozir.getTime() - SIGNAL_OYNASI_KUN * KUN),
  );
  let yozildi = 0;

  for (const [tur, sozlama] of Object.entries(KONTENT_TURLARI)) {
    const qatorlar = db()
      .prepare(
        `select c.id, c.title from content c
           left join homepage_posts p
             on p.source_kind = ? and p.source_id = c.id
          where c.kind = ?
            and c.is_published = 1
            and p.id is null
            and c.created_at >= ?
          order by c.id
          limit ?`,
      )
      .all(sozlama.manba, tur, chegara, BIR_MARTALIK_CHEGARA) as {
      id: unknown;
      title: unknown;
    }[];

    for (const q of qatorlar) {
      const id = songaAylantir(q.id);
      const natija = avtomatikPost(
        sozlama.manba,
        id,
        String(q.title ?? ""),
        sozlama.havola(id),
        hozir,
      );
      if (natija.yangi) yozildi += 1;
    }
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
  kontent: number;
  hisobot: boolean;
} {
  let signal = 0;
  let kontent = 0;
  let hisobot = false;
  // HAR BIRI ALOHIDA `try`: bittasining nosozligi qolganlarini
  // to'xtatmasin. Umumiy `try` bo'lsa, signal so'rovidagi xato
  // hisobotni ham yo'qotardi.
  try {
    signal = signalPostlari(hozir);
  } catch {
    signal = 0;
  }
  try {
    kontent = kontentPostlari(hozir);
  } catch {
    kontent = 0;
  }
  try {
    hisobot = haftalikHisobot(hozir);
  } catch {
    hisobot = false;
  }
  return { signal, kontent, hisobot };
}
