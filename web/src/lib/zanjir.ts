/** Zanjir modulining jonli holati — ekran uchun (4-prompt, 2/3-qism).
 *
 * QAT'IY BIR TOMONLAMA OQIM:
 *
 *     modul -> hisoblaydi -> `zanjir_holatlari` -> ekran
 *
 * Teskarisi TAQIQLANADI: bu yerdagi hech narsa modulga kirish
 * sifatida qaytmaydi va signal qaroriga ta'sir qilmaydi. Eski
 * tizimda aynan shu qoida buzilgan edi — Bozor Salomatligi
 * "ko'rsatkich" deb boshlanib, keyin signalni to'sadigan darvozaga
 * aylangan va tekshirib bo'lmaydigan halqa paydo bo'lgandi.
 *
 * Bu faylda faqat XOM HOLATNI ko'rinishga aylantirish bor. Hisob
 * Pythonda, `core/analysis/` da qoladi.
 */

/** Blokning ekrandagi holati.
 *
 * `tekshirilmagan` — bu coin uchun blok umuman yurmadi (zanjir
 * oldinroq uzilgan). U XIRA, bo'sh kontur bo'lib ko'rinadi. */
export type BlokKorinishi =
  | "toliq" // 4/4 — yorqin, keyingi blokka zanjir ulanadi
  | "qisman" // masalan 2/4 — yarim yorqin
  | "uzilgan" // 0/4 — qizil, zanjir shu yerda uziladi
  | "olchanmadi" // ma'lumot yo'q — zanjirni uzmaydi, lekin kuch ham bermaydi
  | "tekshirilmagan";

export type Blok = {
  nom: string;
  kuch: number;
  maxraj: number;
  otdi: boolean;
  olchanmadi: boolean;
  tosiq: string;
};

export type CoinZanjiri = {
  symbol: string;
  bloklar: Blok[];
  toliq: boolean;
  uzildiBlokda: string | null;
  ishonch: number;
  natija: string;
  izoh: string;
  signalId: number | null;
  tekshirilgan: Date | null;
};

/** To'rt blokning nomlari — zanjir uzilganda ham to'liq qator
 *  chizilishi uchun. Modul faqat YURGAN bloklarni qaytaradi:
 *  Fundamental da uzilsa, qolgan uchtasi umuman hisoblanmaydi. */
export const BLOK_NOMLARI = [
  "Fundamental",
  "Struktura",
  "Zona sifati",
  "Tasdiqlash",
] as const;

/** Bitta blokning ko'rinishini aniqlaydi. */
export function blokKorinishi(blok: Blok | undefined): BlokKorinishi {
  if (!blok) return "tekshirilmagan";
  if (blok.olchanmadi) return "olchanmadi";
  if (blok.maxraj > 0 && blok.kuch === 0) return "uzilgan";
  if (blok.kuch >= blok.maxraj && blok.maxraj > 0) return "toliq";
  return blok.otdi ? "qisman" : "uzilgan";
}

/** Zanjirni to'rtta o'ringa yoyadi — yurmagan bloklar `undefined`.
 *
 * Nima uchun kerak: ekranda zanjir HAR DOIM to'rt bo'g'in bo'lib
 * ko'rinishi kerak. Aks holda Fundamental da uzilgan coin bitta
 * kvadrat bo'lib qolardi va "zanjir qayerda uzildi" degan savolga
 * ko'rinish javob bermasdi. */
export function toliqZanjir(coin: CoinZanjiri): (Blok | undefined)[] {
  return BLOK_NOMLARI.map(
    (nom, i) =>
      coin.bloklar.find((b) => b.nom === nom) ?? coin.bloklar[i] ?? undefined,
  );
}

export type Xulosa = {
  /** Nechta coin tekshirildi (oxirgi yugurishda) */
  jami: number;
  /** To'rtala blok bog'langan coinlar */
  toliq: number;
  /** Signal chiqqanlar */
  signal: number;
  /** O'rtacha nechta blok bog'landi (0-4) */
  ortachaBloklar: number;
  /** Blok nomi -> nechta coin shu yerda uzildi */
  uzilishlar: Record<string, number>;
  /** Eng oxirgi tekshiruv vaqti */
  oxirgi: Date | null;
};

/** Bozor Salomatligi shkalasining qiymati: 0-100.
 *
 * FORMULA — SOF STATISTIKA: o'rtacha nechta blok bog'langani
 * to'rtga nisbatan. Bu raqam modulga HECH NARSA BUYURMAYDI, u
 * faqat "hozir bozorda shart-sharoit qanchalik mos" degan
 * savolning tashqi ko'rsatkichi.
 *
 * Nima uchun ballar yig'indisi emas, blok soni: blok — modulning
 * O'Z birligi. Boshqa formula o'ylab topilsa, u modulda yo'q
 * narsani o'lchagan bo'lardi. */
export function salomatlikIndeksi(xulosa: Xulosa): number | null {
  if (xulosa.jami === 0) return null;
  return Math.round((xulosa.ortachaBloklar / BLOK_NOMLARI.length) * 100);
}

export function xulosaHisobla(coinlar: CoinZanjiri[]): Xulosa {
  // Tekshirilmagan coinlar (ochiq signali borlar) O'RTACHAGA
  // KIRMAYDI: ular "zaif" emas, ular shunchaki tekshirilmagan.
  // Aks holda ochiq signal ko'paygan sari indeks pasayardi va
  // sabab ko'rinmasdi.
  const olchanganlar = coinlar.filter((c) => c.bloklar.length > 0);

  const uzilishlar: Record<string, number> = {};
  for (const c of coinlar) {
    if (c.uzildiBlokda) {
      uzilishlar[c.uzildiBlokda] = (uzilishlar[c.uzildiBlokda] ?? 0) + 1;
    }
  }

  const boglanganlar = olchanganlar.map(
    (c) => c.bloklar.filter((b) => b.otdi && !b.olchanmadi).length,
  );

  const vaqtlar = coinlar
    .map((c) => c.tekshirilgan)
    .filter((d): d is Date => d !== null);

  return {
    jami: olchanganlar.length,
    toliq: coinlar.filter((c) => c.toliq).length,
    signal: coinlar.filter((c) => c.natija === "signal").length,
    ortachaBloklar: boglanganlar.length
      ? boglanganlar.reduce((a, b) => a + b, 0) / boglanganlar.length
      : 0,
    uzilishlar,
    oxirgi: vaqtlar.length
      ? new Date(Math.max(...vaqtlar.map((d) => d.getTime())))
      : null,
  };
}

/** Indeksga SO'Z bilan baho: past / o'rtacha / yaxshi.
 *
 * NEGA KERAK. "72/100" — raqam, lekin u yaxshimi yoki yomonmi degan
 * savolga javob bermaydi. Foydalanuvchi shkalani birinchi marta
 * ko'rganda o'lchov qayerdan boshlanib qayerda tugashini bilmaydi.
 *
 * Chegaralar doira rangi bilan BIR XIL (`components/Doira.tsx`):
 * ikki joyda boshqacha bo'lsa, yashil doira yonida "o'rtacha" degan
 * yozuv turib qolardi.
 */
export function salomatlikTasnifi(indeks: number | null): "past" | "ortacha" | "yaxshi" | null {
  if (indeks === null) return null;
  if (indeks >= 60) return "yaxshi";
  if (indeks >= 35) return "ortacha";
  return "past";
}
