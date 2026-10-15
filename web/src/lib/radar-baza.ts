import { BazaXatosi, db, songaAylantir, vaqt, vaqtSatri } from "./db.ts";
import {
  type KalibrQator,
  type Natija,
  type Sessiya,
  type SessiyaQisqa,
  type SozlamaKalit,
  type YengilNatija,
  manbalarniOqi,
  sozlamaJsonOqi,
  sozlamaKalitmi,
  tekshiruvlarniOqi,
} from "./radar.ts";

/** Modul 4.0.0 — `radar_*` jadvallaridan o'qish va yozish. FAQAT SERVER.
 *
 * Jadvallarni bot (`core/portlash_radari/`) to'ldiradi. Sayt asosan
 * O'QIYDI va faqat uchta joyga yozadi:
 *   1. `radar_holati.sorov`  — "hozir tekshir" bayrog'i;
 *   2. `radar_sozlamalar`    — admin o'zgartirgan chegaralar;
 *   3. `radar_yashirin`      — admin yashirgan coinlar.
 * Sessiya va natijalarga sayt HECH QACHON yozmaydi: hisob botda.
 *
 * Har so'rov tayyorlangan ifoda (`prepare`) va parametr bilan —
 * foydalanuvchi kiritgan matn SQL ga hech qachon yopishtirilmaydi.
 *
 * ESKI BAZA. Migratsiya hali o'tmagan bazada jadval yo'q. Sahifa
 * shunda yiqilmasligi kerak — "radar hali ishga tushmagan" deydi.
 * Shuning uchun avval `radarTayyorligi()` chaqiriladi.
 */

type Qator = Record<string, unknown>;

/** "Jadval yo'q" xatosi — eski bazada kutiladigan holat. */
export function jadvalYoqXatosimi(e: unknown): boolean {
  return e instanceof Error && /no such table/i.test(e.message);
}

/** O'qishni o'raydi: jadval yo'q bo'lsa — bo'sh natija, boshqa xato —
 *  yuqoriga (u haqiqiy muammo va yashirilmasligi kerak). */
function xavfsiz<T>(fn: () => T, zaxira: T): T {
  try {
    return fn();
  } catch (e) {
    if (jadvalYoqXatosimi(e)) return zaxira;
    throw e;
  }
}

export type RadarTayyorligi =
  | { tayyor: true }
  | { tayyor: false; sabab: "jadval_yoq" | "baza_yoq"; izoh: string };

/** Radar jadvallari bormi. Yo'q bo'lsa sahifa bo'sh holatni ko'rsatadi. */
export function radarTayyorligi(): RadarTayyorligi {
  try {
    const q = db()
      .prepare(
        `select count(*) as soni from sqlite_master
          where type = 'table'
            and name in ('radar_sessiyalar', 'radar_natijalar', 'radar_holati',
                         'radar_sozlamalar', 'radar_yashirin')`,
      )
      .get() as Qator | undefined;
    return songaAylantir(q?.soni) === 5
      ? { tayyor: true }
      : { tayyor: false, sabab: "jadval_yoq", izoh: "" };
  } catch (e) {
    if (e instanceof BazaXatosi) {
      return { tayyor: false, sabab: "baza_yoq", izoh: e.message };
    }
    throw e;
  }
}

// --------------------------------------------------------------------------- //
//  Sessiyalar
// --------------------------------------------------------------------------- //

const SESSIYA_USTUNLARI = `id, turi, sham_vaqti, kun, tartib, boshlandi, tugadi, holat,
  universum, darvozadan, elakdan, nomzod, btc_ozgarish, manbalar_json,
  sozlama_json, izoh`;

function son(x: unknown): number | null {
  if (x === null || x === undefined) return null;
  const n = typeof x === "bigint" ? Number(x) : Number(x);
  return Number.isFinite(n) ? n : null;
}

function vaqtOl(x: unknown): Date | null {
  return typeof x === "string" ? vaqt(x) : null;
}

function sessiyaga(q: Qator): Sessiya {
  return {
    id: songaAylantir(q.id),
    turi: String(q.turi ?? ""),
    shamVaqti: vaqtOl(q.sham_vaqti),
    kun: String(q.kun ?? ""),
    tartib: songaAylantir(q.tartib),
    boshlandi: vaqtOl(q.boshlandi),
    tugadi: vaqtOl(q.tugadi),
    holat: String(q.holat ?? ""),
    universum: songaAylantir(q.universum),
    darvozadan: songaAylantir(q.darvozadan),
    elakdan: songaAylantir(q.elakdan),
    nomzod: songaAylantir(q.nomzod),
    btcOzgarish: son(q.btc_ozgarish),
    manbalar: manbalarniOqi(q.manbalar_json),
    sozlama: sozlamaJsonOqi(q.sozlama_json),
    izoh: String(q.izoh ?? ""),
  };
}

/** Oxirgi TUGAGAN sessiya — berilgan turdan.
 *
 * `tasdiq` — rasmiy (B), `qolda` — admin so'ragan tekshiruv. Rasmiy
 * sessiya `sham_vaqti` bo'yicha, qo'lda tekshiruv esa boshlangan
 * vaqti bo'yicha tartiblanadi (uning shami ma'nosiz).
 */
export function oxirgiSessiya(turi: "tasdiq" | "qolda" | "kashfiyot"): Sessiya | null {
  return xavfsiz(() => {
    const tartib = turi === "qolda" ? "boshlandi desc, id desc" : "sham_vaqti desc, id desc";
    const q = db()
      .prepare(
        `select ${SESSIYA_USTUNLARI} from radar_sessiyalar
          where turi = ? and holat = 'tugadi'
          order by ${tartib} limit 1`,
      )
      .get(turi) as Qator | undefined;
    return q ? sessiyaga(q) : null;
  }, null);
}

/** Eng oxirgi sessiya (holatidan qat'i nazar) — "hozir yurmoqda"
 *  yoki "xato bilan tugadi" ni ko'rsatish uchun. */
export function engSonggiSessiya(): Sessiya | null {
  return xavfsiz(() => {
    const q = db()
      .prepare(
        `select ${SESSIYA_USTUNLARI} from radar_sessiyalar
          order by boshlandi desc, id desc limit 1`,
      )
      .get() as Qator | undefined;
    return q ? sessiyaga(q) : null;
  }, null);
}

/** Kunlar oralig'idagi RASMIY (B) sessiyalar — hamma holatda.
 *  Qaysi biri "bor", qaysi biri "o'tkazib yuborilgan" — `radar.ts`
 *  hal qiladi. */
export function rasmiySessiyalar(kunDan: string, kunGacha: string): SessiyaQisqa[] {
  return xavfsiz(() => {
    const qatorlar = db()
      .prepare(
        `select id, kun, tartib, holat from radar_sessiyalar
          where turi = 'tasdiq' and kun >= ? and kun <= ?
          order by kun, tartib, id`,
      )
      .all(kunDan, kunGacha) as Qator[];
    return qatorlar.map((q) => ({
      id: songaAylantir(q.id),
      kun: String(q.kun ?? ""),
      tartib: songaAylantir(q.tartib),
      holat: String(q.holat ?? ""),
    }));
  }, []);
}

/** Eng birinchi rasmiy sessiya — radar qachondan beri ishlaydi.
 *  Undan oldingi ustunlar "o'tkazib yuborildi" deb ko'rsatilmaydi. */
export function birinchiRasmiySlot(): { kun: string; tartib: number } | null {
  return xavfsiz(() => {
    const q = db()
      .prepare(
        `select kun, tartib from radar_sessiyalar
          where turi = 'tasdiq' order by kun, tartib limit 1`,
      )
      .get() as Qator | undefined;
    return q ? { kun: String(q.kun ?? ""), tartib: songaAylantir(q.tartib) } : null;
  }, null);
}

/** `kun` dan OLDINGI eng so'nggi tugagan rasmiy sessiya.
 *
 * Jadvalning birinchi ustuni foizi shundan hisoblanadi — u oldingi
 * kunda (yoki undan ham oldin, agar sessiyalar o'tkazib yuborilgan
 * bo'lsa) bo'lishi mumkin. `sham_vaqti` emas, `kun`+`tartib` bilan:
 * vaqt satrining formati bazaga qarab farq qilishi mumkin, kun esa
 * doim `YYYY-MM-DD`.
 */
export function oldingiRasmiySessiyaId(kun: string): number | null {
  return xavfsiz(() => {
    const q = db()
      .prepare(
        `select id from radar_sessiyalar
          where turi = 'tasdiq' and holat = 'tugadi' and kun < ?
          order by kun desc, tartib desc, id desc limit 1`,
      )
      .get(kun) as Qator | undefined;
    return q ? songaAylantir(q.id) : null;
  }, null);
}

// --------------------------------------------------------------------------- //
//  Natijalar
// --------------------------------------------------------------------------- //

function bool(x: unknown): boolean {
  return Number(x ?? 0) !== 0;
}

/** `in (?, ?, ...)` — joy belgilari SONI id lar sonidan yasaladi,
 *  qiymatlarning o'zi esa parametr bo'lib uzatiladi. SQLite bitta
 *  so'rovda 999 tagacha parametr oladi — shuning uchun bo'laklab. */
function bolaklab<T>(idlar: number[], fn: (bolak: number[]) => T[]): T[] {
  const natija: T[] = [];
  const toza = [...new Set(idlar.filter((x) => Number.isInteger(x)))];
  for (let i = 0; i < toza.length; i += 500) {
    natija.push(...fn(toza.slice(i, i + 500)));
  }
  return natija;
}

/** Grafik va jadval uchun — faqat kerakli ustunlar. */
export function yengilNatijalar(sessiyaIdlar: number[]): YengilNatija[] {
  return xavfsiz(
    () =>
      bolaklab(sessiyaIdlar, (bolak) => {
        const joylar = bolak.map(() => "?").join(", ");
        const qatorlar = db()
          .prepare(
            `select sessiya_id, symbol, belgi, turi, orin, narx, holat
               from radar_natijalar where sessiya_id in (${joylar})`,
          )
          .all(...bolak) as Qator[];
        return qatorlar.map(
          (q): YengilNatija => ({
            sessiyaId: songaAylantir(q.sessiya_id),
            symbol: String(q.symbol ?? ""),
            belgi: String(q.belgi ?? q.symbol ?? ""),
            turi: String(q.turi ?? ""),
            orin: son(q.orin),
            narx: son(q.narx),
            holat: holatOl(q.holat),
          }),
        );
      }),
    [],
  );
}

function holatOl(x: unknown): Natija["holat"] {
  return x === "tasdiqlangan" || x === "vaqtinchalik" || x === "nomzod" ? x : "oddiy";
}

function halolOl(x: unknown): Natija["halol"] {
  return x === "halol" || x === "harom" || x === "shubhali" ? x : "baholanmagan";
}

/** Bitta sessiyaning to'liq natijalari — kartochkalar uchun. */
export function sessiyaNatijalari(sessiyaId: number): Natija[] {
  return xavfsiz(() => {
    const qatorlar = db()
      .prepare(
        `select sessiya_id, symbol, belgi, turi, narx, hajm_24s, hajm_nisbati,
                ozgarish_24s, market_cap, tekshiruvlar_json, tasdiq_soni,
                harakat_soni, yoqilgi_soni, malumot_yoq_soni, nomzod, holat,
                orin, ketma_ket, yashirin, yangi_listing, halol
           from radar_natijalar where sessiya_id = ?`,
      )
      .all(sessiyaId) as Qator[];
    return qatorlar.map(
      (q): Natija => ({
        sessiyaId: songaAylantir(q.sessiya_id),
        symbol: String(q.symbol ?? ""),
        belgi: String(q.belgi ?? q.symbol ?? ""),
        turi: String(q.turi ?? ""),
        narx: son(q.narx),
        hajm24s: son(q.hajm_24s),
        hajmNisbati: son(q.hajm_nisbati),
        ozgarish24s: son(q.ozgarish_24s),
        marketCap: son(q.market_cap),
        tekshiruvlar: tekshiruvlarniOqi(q.tekshiruvlar_json),
        tasdiqSoni: songaAylantir(q.tasdiq_soni),
        harakatSoni: songaAylantir(q.harakat_soni),
        yoqilgiSoni: songaAylantir(q.yoqilgi_soni),
        malumotYoqSoni: songaAylantir(q.malumot_yoq_soni),
        nomzod: bool(q.nomzod),
        holat: holatOl(q.holat),
        orin: son(q.orin),
        ketmaKet: songaAylantir(q.ketma_ket),
        yashirin: bool(q.yashirin),
        yangiListing: bool(q.yangi_listing),
        halol: halolOl(q.halol),
      }),
    );
  }, []);
}

/** Calibration qatorlari — rasmiy sessiyalar, `kunDan` dan beri.
 *
 * Faqat `elak` va `namuna` (`chiqdi` da faqat narx bor) va kamida
 * 24 soatlik bahosi bor qatorlar. Oyna cheklangan (~60 kun): sahifa
 * har ochilishda butun tarixni o'qimasin.
 */
export function kalibrQatorlari(kunDan: string): KalibrQator[] {
  return xavfsiz(() => {
    const qatorlar = db()
      .prepare(
        `select n.turi, n.nomzod, n.tasdiq_soni, n.tekshiruvlar_json,
                n.kel_24s_max, n.kel_24s_min, n.kel_7k_max, n.kel_7k_min
           from radar_natijalar n
           join radar_sessiyalar s on s.id = n.sessiya_id
          where s.turi = 'tasdiq' and s.holat = 'tugadi' and s.kun >= ?
            and n.turi in ('elak', 'namuna')
            and (n.kel_24s_max is not null or n.kel_7k_max is not null)`,
      )
      .all(kunDan) as Qator[];
    return qatorlar.map(
      (q): KalibrQator => ({
        turi: String(q.turi ?? ""),
        nomzod: bool(q.nomzod),
        tasdiqSoni: songaAylantir(q.tasdiq_soni),
        tekshiruvlar: tekshiruvlarniOqi(q.tekshiruvlar_json),
        kel24Max: son(q.kel_24s_max),
        kel24Min: son(q.kel_24s_min),
        kel7Max: son(q.kel_7k_max),
        kel7Min: son(q.kel_7k_min),
      }),
    );
  }, []);
}

// --------------------------------------------------------------------------- //
//  Ishchi holati
// --------------------------------------------------------------------------- //

export type RadarHolati = {
  sorov: boolean;
  ishchiTirik: Date | null;
  hajmYangilandi: Date | null;
  baholashOxirgi: Date | null;
  oxirgiXato: string;
};

export function radarHolati(): RadarHolati {
  return xavfsiz(
    () => {
      const q = db()
        .prepare(
          `select sorov, ishchi_tirik, hajm_yangilandi, baholash_oxirgi, oxirgi_xato
             from radar_holati where id = 1`,
        )
        .get() as Qator | undefined;
      return {
        sorov: bool(q?.sorov),
        ishchiTirik: vaqtOl(q?.ishchi_tirik),
        hajmYangilandi: vaqtOl(q?.hajm_yangilandi),
        baholashOxirgi: vaqtOl(q?.baholash_oxirgi),
        oxirgiXato: String(q?.oxirgi_xato ?? ""),
      };
    },
    { sorov: false, ishchiTirik: null, hajmYangilandi: null, baholashOxirgi: null, oxirgiXato: "" },
  );
}

/** Admin "hozir tekshir" bosdi — botga BUYRUQ qoldiriladi.
 *
 * Sayt sessiyani O'ZI yurgizmaydi: u faqat bayroq qo'yadi, bot uni
 * keyingi aylanishda ko'rib `qolda` sessiyasini boshlaydi va bayroqni
 * tushiradi (`kuzatuvSkaniSora` bilan bir xil usul).
 */
export function radarSora(): void {
  db()
    .prepare(
      `insert into radar_holati (id, sorov) values (1, 1)
       on conflict(id) do update set sorov = 1, updated_at = current_timestamp`,
    )
    .run();
}

// --------------------------------------------------------------------------- //
//  Sozlamalar
// --------------------------------------------------------------------------- //

export type SozlamaOverride = {
  kalit: SozlamaKalit;
  qiymat: number;
  ozgartirdi: number | null;
  yangilangan: Date | null;
};

/** Admin bosib qo'ygan chegaralar. Noma'lum kalit (eski versiyadan
 *  qolgan) jimgina tashlanadi. */
export function sozlamaOverridelari(): Map<SozlamaKalit, SozlamaOverride> {
  return xavfsiz(() => {
    const qatorlar = db()
      .prepare(`select kalit, qiymat, ozgartirdi, updated_at from radar_sozlamalar`)
      .all() as Qator[];
    const natija = new Map<SozlamaKalit, SozlamaOverride>();
    for (const q of qatorlar) {
      const kalit = String(q.kalit ?? "");
      const qiymat = son(q.qiymat);
      if (!sozlamaKalitmi(kalit) || qiymat === null) continue;
      natija.set(kalit, {
        kalit,
        qiymat,
        ozgartirdi: son(q.ozgartirdi),
        yangilangan: vaqtOl(q.updated_at),
      });
    }
    return natija;
  }, new Map());
}

/** Chegarani saqlash. Qiymat OLDINDAN `sozlamaTekshir` dan o'tgan
 *  bo'lishi shart — bu funksiya faqat yozadi. */
export function sozlamaYoz(kalit: SozlamaKalit, qiymat: number, ozgartirdi: number | null): void {
  db()
    .prepare(
      `insert into radar_sozlamalar (kalit, qiymat, ozgartirdi) values (?, ?, ?)
       on conflict(kalit) do update set
         qiymat = excluded.qiymat,
         ozgartirdi = excluded.ozgartirdi,
         updated_at = current_timestamp`,
    )
    .run(kalit, qiymat, ozgartirdi);
}

/** "Standartga qaytarish" — qator o'chadi, YAML qiymati kuchga kiradi. */
export function sozlamaOchir(kalit: SozlamaKalit): void {
  db().prepare(`delete from radar_sozlamalar where kalit = ?`).run(kalit);
}

// --------------------------------------------------------------------------- //
//  Yashirin coinlar
// --------------------------------------------------------------------------- //

export type YashirinCoin = {
  symbol: string;
  sabab: string;
  /** `null` — doimiy */
  gacha: Date | null;
  qoshdi: number | null;
  qoshilgan: Date | null;
};

export function yashirinlar(): YashirinCoin[] {
  return xavfsiz(() => {
    const qatorlar = db()
      .prepare(
        `select symbol, sabab, gacha, qoshdi, created_at
           from radar_yashirin order by symbol`,
      )
      .all() as Qator[];
    return qatorlar.map((q) => ({
      symbol: String(q.symbol ?? ""),
      sabab: String(q.sabab ?? ""),
      gacha: vaqtOl(q.gacha),
      qoshdi: son(q.qoshdi),
      qoshilgan: vaqtOl(q.created_at),
    }));
  }, []);
}

/** Coinni yashirish (yoki muddatini yangilash). `symbol` OLDINDAN
 *  `symbolNormalla` dan o'tgan bo'lishi shart. */
export function yashirinQosh(
  symbol: string,
  sabab: string,
  gacha: Date | null,
  qoshdi: number | null,
): void {
  db()
    .prepare(
      `insert into radar_yashirin (symbol, sabab, gacha, qoshdi) values (?, ?, ?, ?)
       on conflict(symbol) do update set
         sabab = excluded.sabab,
         gacha = excluded.gacha,
         qoshdi = excluded.qoshdi,
         updated_at = current_timestamp`,
    )
    .run(symbol, sabab, gacha ? vaqtSatri(gacha) : null, qoshdi);
}

export function yashirinOchir(symbol: string): void {
  db().prepare(`delete from radar_yashirin where symbol = ?`).run(symbol);
}
