import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { MENYU } from "../src/lib/menyu.ts";
import {
  SEGMENT_KALITI,
  SEGMENT_SONI,
  blokRangi,
  likvidlik,
  muomalaUlushi,
  sutkalikOrin,
  yonalishBelgisi,
  zonaJoyi,
  type KuzatuvBlok,
} from "../src/lib/kuzatuv.ts";

const ILDIZ = path.join(import.meta.dirname, "..", "..");

function oqi(nisbiy: string): string {
  return readFileSync(path.join(ILDIZ, nisbiy), "utf8");
}

// --------------------------------------------------------------------------- //
//  CHEGARA — sayt tomonida ham Entry/Stop/TP yo'q
// --------------------------------------------------------------------------- //

const SAYT_FAYLLARI = [
  "web/src/lib/kuzatuv.ts",
  "web/src/components/kuzatuv/Segmentlar.tsx",
  "web/src/components/kuzatuv/CoinQatori.tsx",
  "web/src/app/(ichki)/kuzatuv/page.tsx",
  "web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx",
];

test("kuzatuv sahifalari savdo darajasi hisoblamaydi", () => {
  // `kalkulyator` va `signal.kalk_*` — Entry/Stop/TP bilan ishlaydigan
  // mavjud modullar. Ular kuzatuv paneliga KIRMASLIGI kerak.
  const taqiq = ["kalkulyatorMatnlari", "signalLevels", "darajalarQur", "@/lib/kalkulyator"];
  for (const fayl of SAYT_FAYLLARI) {
    const matn = oqi(fayl);
    for (const nom of taqiq) {
      assert.ok(!matn.includes(nom), `${fayl}: taqiqlangan "${nom}" ishlatilgan`);
    }
  }
});

test("chegara ro'yxati bo'sh emas", () => {
  // Ro'yxat bo'shab qolsa yuqoridagi test YOLG'ON yashil berardi.
  assert.ok(SAYT_FAYLLARI.length >= 5);
  for (const fayl of SAYT_FAYLLARI) {
    assert.ok(oqi(fayl).length > 0, `${fayl} bo'sh`);
  }
});

// --------------------------------------------------------------------------- //
//  Python bilan mos
// --------------------------------------------------------------------------- //

test("segment nomlari Python bilan bir xil", () => {
  const python = oqi("core/analysis/observation_mode.py");
  for (const nom of Object.keys(SEGMENT_KALITI)) {
    assert.ok(
      python.includes(`"${nom}"`),
      `segment "${nom}" Pythonda topilmadi — nomlar ajralib ketgan`,
    );
  }
});

test("segment soni ikki tomonda teng", () => {
  assert.equal(SEGMENT_SONI, Object.keys(SEGMENT_KALITI).length);
});

test("yo'nalish qiymatlari Python bilan bir xil", () => {
  const python = oqi("core/analysis/structure/uptrend_filter.py");
  for (const qiymat of ["uptrend", "yangi_burilish", "downtrend", "aniq_emas"]) {
    assert.ok(python.includes(`"${qiymat}"`), `yo'nalish "${qiymat}" Pythonda yo'q`);
  }
});

test("ro'yxat nomlari Python bilan bir xil", () => {
  const python = oqi("core/watch_panel/repository.py");
  for (const qiymat of ["top", "kuzatuvda", "royxatdan_tashqari"]) {
    assert.ok(python.includes(`"${qiymat}"`), `ro'yxat "${qiymat}" Pythonda yo'q`);
  }
});

// --------------------------------------------------------------------------- //
//  Menyu — faqat admin
// --------------------------------------------------------------------------- //

test("kuzatuv paneli FAQAT adminlarga ko'rinadi", () => {
  const band = MENYU.find((b) => b.kod === "kuzatuv");
  assert.ok(band, "menyuda kuzatuv bandi yo'q");
  assert.equal(band.adminUchun, true);
  assert.equal(band.yol, "/kuzatuv");
});

test("sahifaning O'ZI ham adminlikni tekshiradi", () => {
  // Menyuda yashirish YETARLI EMAS: manzilni bilgan har kim
  // sahifani ochishi mumkin.
  for (const fayl of [
    "web/src/app/(ichki)/kuzatuv/page.tsx",
    "web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx",
  ]) {
    assert.ok(oqi(fayl).includes("if (!admin)"), `${fayl}: adminlik tekshirilmagan`);
  }
});

test("server amali ham adminlikni qayta tekshiradi", () => {
  // Server amali ALOHIDA so'rov bo'lib keladi va layout u uchun
  // yugurmaydi.
  const matn = oqi("web/src/app/(ichki)/kuzatuv/amallar.ts");
  assert.ok(matn.includes("if (!admin) return"));
});

// --------------------------------------------------------------------------- //
//  Zona joyi
// --------------------------------------------------------------------------- //

test("zona joyi: pastki qismda discount", () => {
  assert.equal(zonaJoyi(102, 100, 200), "discount");
});

test("zona joyi: yuqori qismda premium", () => {
  assert.equal(zonaJoyi(190, 100, 200), "premium");
});

test("zona joyi: o'rtada", () => {
  assert.equal(zonaJoyi(150, 100, 200), "ortada");
});

test("zona joyi: ma'lumot yo'q bo'lsa nomalum", () => {
  assert.equal(zonaJoyi(null, 100, 200), "nomalum");
  assert.equal(zonaJoyi(150, null, 200), "nomalum");
  // Teskari oraliq — bo'linish nolga ketmasin
  assert.equal(zonaJoyi(150, 200, 100), "nomalum");
  assert.equal(zonaJoyi(Number.NaN, 100, 200), "nomalum");
});

// --------------------------------------------------------------------------- //
//  Ko'rinish qoidalari
// --------------------------------------------------------------------------- //

test("yo'nalish ikonkasi har qiymat uchun bor", () => {
  const nomlar = new Set(
    (["uptrend", "yangi_burilish", "downtrend", "aniq_emas"] as const).map(
      yonalishBelgisi,
    ),
  );
  assert.equal(nomlar.size, 4, "ikki yo'nalish bir xil ikonka olgan");
});

test("o'lchanmagan blok 'yo'q' EMAS — uchinchi rang", () => {
  const asos = { nom: "Fundamental", kuch: 0, maxraj: 0, tosiq: null, tekshiruvlar: [] };
  const olchanmadi: KuzatuvBlok = { ...asos, otdi: true, olchanmadi: true };
  const otmadi: KuzatuvBlok = { ...asos, maxraj: 4, otdi: false, olchanmadi: false };
  const otdi: KuzatuvBlok = { ...asos, maxraj: 4, kuch: 2, otdi: true, olchanmadi: false };

  assert.equal(blokRangi(olchanmadi), "sokin");
  assert.equal(blokRangi(otmadi), "past");
  assert.equal(blokRangi(otdi), "yaxshi");
});

// --------------------------------------------------------------------------- //
//  Tarjima
// --------------------------------------------------------------------------- //

test("uz va ru da bir xil kuzatuv kalitlari bor", () => {
  const uz = JSON.parse(oqi("web/src/lib/i18n/uz.json")) as Record<string, unknown>;
  const ru = JSON.parse(oqi("web/src/lib/i18n/ru.json")) as Record<string, unknown>;

  const kalitlar = (obj: unknown, oldin = ""): string[] => {
    if (typeof obj !== "object" || obj === null) return [oldin];
    return Object.entries(obj).flatMap(([k, v]) => kalitlar(v, oldin ? `${oldin}.${k}` : k));
  };

  const uzKalit = kalitlar(uz.kuzatuv).sort();
  const ruKalit = kalitlar(ru.kuzatuv).sort();
  assert.ok(uzKalit.length > 20, "kuzatuv tarjimasi juda kam");
  assert.deepEqual(uzKalit, ruKalit, "uz va ru kalitlari mos emas");
});

test("har bir segment kaliti tarjimada bor", () => {
  const uz = JSON.parse(oqi("web/src/lib/i18n/uz.json")) as Record<string, unknown>;
  for (const kalit of Object.values(SEGMENT_KALITI)) {
    const yol = kalit.split(".");
    let joriy: unknown = uz;
    for (const bolak of yol) {
      joriy = (joriy as Record<string, unknown>)?.[bolak];
    }
    assert.equal(typeof joriy, "string", `tarjima yo'q: ${kalit}`);
  }
});

// --------------------------------------------------------------------------- //
//  Qidiruv sahifasi (7-qism)
// --------------------------------------------------------------------------- //

test("qidiruv sahifasi FAQAT Top 20 ni ko'rsatadi", () => {
  // "+10 kuzatuvda" — admin uchun. Foydalanuvchiga u chiqmasligi
  // kerak, aks holda hali tayyor bo'lmagan coin "tavsiya" bo'lib
  // ko'rinardi.
  const matn = oqi("web/src/app/(ichki)/qidiruv/page.tsx");
  assert.ok(matn.includes('royxat === "top"'), "Top 20 filtri yo'q");
});

test("qidiruv sahifasi admin tafsilotini ko'rsatmaydi", () => {
  const matn = oqi("web/src/app/(ichki)/qidiruv/page.tsx");
  for (const taqiq of [
    "JonliStakan",
    "xaridBosimi",
    "yiriklar",
    "segmentlar",
    "bloklar",
  ]) {
    assert.ok(!matn.includes(taqiq), `foydalanuvchiga "${taqiq}" chiqmasligi kerak`);
  }
});

test("qidiruv sahifasida ham savdo darajasi yo'q", () => {
  const matn = oqi("web/src/app/(ichki)/qidiruv/page.tsx");
  for (const taqiq of ["kalkulyatorMatnlari", "@/lib/kalkulyator", "signalLevels"]) {
    assert.ok(!matn.includes(taqiq), `taqiqlangan "${taqiq}" ishlatilgan`);
  }
});

test("chegara raqamlari YAML dan o'qiladi, kodda qattiq yozilmagan", () => {
  // Ikki nusxa bo'lsa, bir kuni YAML o'zgartiriladi-yu saytda
  // eskisi qolib ketardi.
  const matn = oqi("web/src/lib/queries.ts");
  assert.ok(matn.includes('sozlama(["kuzatuv", "qidiruv_premium"]'));
  assert.ok(matn.includes('sozlama(["kuzatuv", "qidiruv_obunasiz"]'));

  const yaml = oqi("config/default.yaml");
  for (const kalit of [
    "qidiruv_obunasiz",
    "qidiruv_lite",
    "qidiruv_pro",
    "qidiruv_premium",
  ]) {
    assert.ok(yaml.includes(kalit), `YAML da ${kalit} yo'q`);
  }
});

test("qidiruv menyuda HAMMAGA ochiq", () => {
  const band = MENYU.find((b) => b.kod === "qidiruv");
  assert.ok(band, "menyuda qidiruv bandi yo'q");
  assert.equal(band.talab, null);
  assert.notEqual(band.adminUchun, true);
});

test("timeframe qiymatlari YAML va Python da bir xil", () => {
  const yaml = oqi("config/default.yaml");
  const python = oqi("core/analysis/observation_mode.py");
  for (const tf of ["4h", "1h", "15m"]) {
    assert.ok(yaml.includes(`"${tf}"`), `YAML da ${tf} yo'q`);
    assert.ok(python.includes(`"${tf}"`), `Pythonda ${tf} yo'q`);
  }
});

// --------------------------------------------------------------------------- //
//  Alternativ yo'llar (1-qism: "TO'LIQ SAQLANADI")
// --------------------------------------------------------------------------- //

test("Rejim B alternativ yo'llarni chaqiradi", () => {
  // Bu — birinchi yozuvda TUSHIB QOLGAN qism. Alternativ usullar
  // `alternative_chain.py` ichida, zanjir mantig'i bilan bir
  // faylda turadi; o'sha fayldan qochganda ular ham yo'qolgan edi.
  const python = oqi("core/analysis/observation_mode.py");
  for (const nom of ["alternativlar_2", "alternativlar_3", "alternativlar_4", "qutqar"]) {
    assert.ok(python.includes(nom), `alternativ yo'l chaqirilmagan: ${nom}`);
  }
});

test("alternativ mantig'i KO'CHIRILMAGAN, import qilingan", () => {
  // Ikki nusxa bo'lsa, ular vaqt o'tib ajralib ketardi.
  const python = oqi("core/analysis/observation_mode.py");
  assert.ok(
    python.includes("from core.analysis.alternatives.alternative_chain import"),
    "alternativ mantig'i o'z joyidan import qilinmagan",
  );
});

test("g'olib alternativ ekranda ko'rinadi", () => {
  // 5.3-qism: "qaysi usul ishlagani ko'rsatiladi".
  const sahifa = oqi("web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx");
  assert.ok(sahifa.includes('startsWith("alternativ:")'));
  assert.ok(sahifa.includes('t("kuzatuv.alternativ")'));

  const uz = JSON.parse(oqi("web/src/lib/i18n/uz.json")) as {
    kuzatuv: Record<string, unknown>;
  };
  assert.equal(typeof uz.kuzatuv.alternativ, "string");
});

// --------------------------------------------------------------------------- //
//  Bozor ma'lumoti — TO'LIQ to'plam (loyiha egasi: "ma'lumotlar yuzaki")
// --------------------------------------------------------------------------- //

test("CoinGecko javobidan asosiy maydonlar OLINADI", () => {
  // Ular bitta so'rovda keladi. Ilgari beshtasi olinib qolgani
  // bekorga tashlab yuborilardi.
  const python = oqi("core/watch_panel/cmc_snapshot.py");
  for (const maydon of [
    "market_cap_rank",
    "fully_diluted_valuation",
    "circulating_supply",
    "total_supply",
    "max_supply",
    "ath",
    "ath_change_percentage",
    "atl",
    "high_24h",
    "low_24h",
  ]) {
    assert.ok(python.includes(`"${maydon}"`), `CoinGecko maydoni olinmagan: ${maydon}`);
  }
});

test("likvidlik ko'rsatkichi ALOHIDA ustun emas, hisoblanadi", () => {
  // Uchinchi nusxa saqlash — ular ajralib ketishining eng oson yo'li.
  assert.equal(likvidlik({ hajm24s: 50, marketCap: 1000 }), 5);
  assert.equal(likvidlik({ hajm24s: null, marketCap: 1000 }), null);
  // Nolga bo'linish
  assert.equal(likvidlik({ hajm24s: 50, marketCap: 0 }), null);
  assert.equal(likvidlik({ hajm24s: 50, marketCap: null }), null);
});

test("muomala ulushi: max yo'q bo'lsa jami dan hisoblanadi", () => {
  assert.equal(
    muomalaUlushi({ muomalada: 50, engKopToken: 100, jamiToken: 200 }),
    50,
  );
  // Cheksiz emissiyali coin — `max_supply` yo'q
  assert.equal(
    muomalaUlushi({ muomalada: 50, engKopToken: null, jamiToken: 200 }),
    25,
  );
  assert.equal(
    muomalaUlushi({ muomalada: null, engKopToken: 100, jamiToken: null }),
    null,
  );
});

test("sutkalik o'rin 0..100 dan chiqmaydi", () => {
  assert.equal(sutkalikOrin(150, 100, 200), 50);
  assert.equal(sutkalikOrin(100, 100, 200), 0);
  assert.equal(sutkalikOrin(200, 100, 200), 100);
  // Oraliqdan tashqarida — chegaraga qisiladi, manfiy chiqmaydi
  assert.equal(sutkalikOrin(50, 100, 200), 0);
  assert.equal(sutkalikOrin(250, 100, 200), 100);
  // Teskari yoki yassi oraliq
  assert.equal(sutkalikOrin(150, 200, 100), null);
  assert.equal(sutkalikOrin(150, 100, 100), null);
});

test("bozor kartasi BITTA joyda — ikki sahifa o'shani ishlatadi", () => {
  // Ikki nusxa qilinsa, yangi ko'rsatkich qo'shilganda biri
  // yangilanib ikkinchisi qolib ketardi.
  for (const sahifa of [
    "web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx",
    "web/src/app/(ichki)/qidiruv/page.tsx",
  ]) {
    assert.ok(oqi(sahifa).includes("BozorKesimi"), `${sahifa}: umumiy karta ishlatilmagan`);
  }
});

test("FDV va ta'minot FAQAT adminga ko'rinadi", () => {
  // `toliq` bayrog'i — admin sahifasida bor, qidiruvda YO'Q.
  const admin = oqi("web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx");
  const qidiruv = oqi("web/src/app/(ichki)/qidiruv/page.tsx");
  assert.ok(admin.includes("toliq"), "admin sahifasida to'liq ko'rinish yo'q");
  assert.ok(
    !/<BozorKesimi[^>]*toliq/.test(qidiruv),
    "qidiruv sahifasida to'liq ko'rinish ochilgan",
  );
});

// --------------------------------------------------------------------------- //
//  IKKINCHI DARVOZA — "allaqachon yurgan" coin ro'yxatga kirmaydi
// --------------------------------------------------------------------------- //

test("bosqich darvozasi Pythonda bor", () => {
  // Loyiha egasi ekranda ko'rgan xato: HH/HL to'g'ri, lekin coin
  // allaqachon yurib bo'lgan. Yo'nalish bu holatni ushlay olmaydi.
  const python = oqi("core/analysis/observation_mode.py");
  assert.ok(python.includes("bosqich_aniqla"), "bosqich darvozasi chaqirilmagan");
  assert.ok(
    python.includes("self.yonalish.otadi and self.bosqich.nomzod"),
    "ikkala darvoza birga tekshirilmagan",
  );
});

test("bosqich qiymatlari ikki tomonda bir xil", () => {
  const python = oqi("core/analysis/structure/uptrend_filter.py");
  for (const qiymat of ["korreksiya", "chuqur", "yurgan", "nomalum"]) {
    assert.ok(python.includes(`"${qiymat}"`), `bosqich "${qiymat}" Pythonda yo'q`);
  }
});

test("YURGAN — yagona nomzod BO'LMAGAN bosqich", () => {
  // Impuls topilmasligi ("nomalum") coinni chetlatmaydi: bilmaslik
  // salbiy javob emas.
  const python = oqi("core/analysis/structure/uptrend_filter.py");
  assert.ok(python.includes("return self is not Bosqich.YURGAN"));
});

test("zona joyi JORIY narx bilan hisoblanadi, zona markazi bilan emas", () => {
  // Birinchi yozuvda bu yerga zona markazi berilgan edi va ustun
  // HAR DOIM "o'rtada" ko'rsatardi — markazning nisbati doim 0.5.
  const qator = oqi("web/src/components/kuzatuv/CoinQatori.tsx");
  assert.ok(
    qator.includes("zonaJoyi(coin.narx, coin.impulsPast, coin.impulsYuqori)"),
    "zona joyi hali ham noto'g'ri hisoblanmoqda",
  );
  assert.ok(
    !qator.includes("zonaYuqori) / 2"),
    "zona markazi hali ham ishlatilmoqda",
  );
});

test("zona markazi berilsa natija DOIM 'ortada' — eski xatoning isboti", () => {
  // Bu test xatoning O'ZINI hujjatlashtiradi: markaz nisbati doim
  // 0.5, ya'ni javob ma'lumotdan MUSTAQIL edi.
  for (const [past, yuqori] of [
    [100, 200],
    [1, 1000],
    [0.5, 0.9],
  ] as const) {
    assert.equal(zonaJoyi((past + yuqori) / 2, past, yuqori), "ortada");
  }
  // Haqiqiy narx bilan esa javob o'zgaradi
  assert.equal(zonaJoyi(110, 100, 200), "discount");
  assert.equal(zonaJoyi(190, 100, 200), "premium");
});

// --------------------------------------------------------------------------- //
//  PROMPTDAN QOLIB KETGAN TALABLAR (5.3 va 6-qism)
// --------------------------------------------------------------------------- //

test("5.3: ANIQ NARX darajalari ko'rsatiladi", () => {
  // Prompt uch marta "ANIQ NARX" so'raydi. Blok tekshiruvlarining
  // izohida bu raqamlar YO'Q — ular faqat "bor/yo'q" deydi.
  const sahifa = oqi("web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx");
  for (const kalit of [
    "kuzatuv.support",
    "kuzatuv.resistance",
    "kuzatuv.bos_daraja",
    "kuzatuv.sweep_daraja",
  ]) {
    assert.ok(sahifa.includes(kalit), `narx darajasi ko'rsatilmagan: ${kalit}`);
  }
});

test("5.3: BOS va sweep darajalari Pythonda hisoblanadi", () => {
  const python = oqi("core/analysis/observation_mode.py");
  assert.ok(python.includes("bos_choch_topish"), "BOS darajasi olinmagan");
  assert.ok(python.includes("sweep_narx"), "sweep darajasi olinmagan");
});

test("5.3: har blok kartasida IKONKA bor", () => {
  const sahifa = oqi("web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx");
  assert.ok(sahifa.includes("BLOK_IKONKASI"), "blok ikonkalari yo'q");
  // To'rt blokning HAMMASIGA ikonka berilgan
  for (const nom of ["Fundamental", "Struktura", "Zona Sifati", "Tasdiqlash"]) {
    assert.ok(
      new RegExp(`BLOK_IKONKASI[\\s\\S]*?["']?${nom}["']?:`).test(sahifa),
      `${nom} uchun ikonka yo'q`,
    );
  }
});

test("6-qism: KATTA OPERATSIYALAR ro'yxati chiziladi", () => {
  // Ilgari faqat SONI ko'rsatilardi, ro'yxatning o'zi yo'q edi.
  const stakan = oqi("web/src/components/kuzatuv/JonliStakan.tsx");
  assert.ok(stakan.includes("yiriklar"), "yirik operatsiyalar ro'yxati yo'q");
  assert.ok(stakan.includes("yiriklarRoyxat"));

  const sahifa = oqi("web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx");
  assert.ok(sahifa.includes("yiriklar={bozor?.yiriklar"), "ro'yxat uzatilmagan");
});

test("6-qism: JONLI narx oqimdan olinadi, bazadan emas", () => {
  // Bazadagi narx skan paytidagi — soatlab eskirgan bo'lishi mumkin.
  const stakan = oqi("web/src/components/kuzatuv/JonliStakan.tsx");
  assert.ok(stakan.includes("const jonliNarx = lenta[0]?.narx"));
  assert.ok(stakan.includes("jonliNarx"));
});

test("6-qism: CoinGecko jadvali IKONKALI", () => {
  const kesim = oqi("web/src/components/kuzatuv/BozorKesimi.tsx");
  assert.ok(kesim.includes("belgi?: IkonkaNomi"), "ikonka maydoni yo'q");
  // Asosiy uch qatorda ikonka bor
  for (const belgi of ['belgi="pul"', 'belgi="hajm"', 'belgi="onchain"']) {
    assert.ok(kesim.includes(belgi), `ikonka berilmagan: ${belgi}`);
  }
});

test("zona timeframe'i QO'LDA yozilmagan", () => {
  // Config o'zgarsa, ekrandagi yozuv ham o'zgarishi kerak.
  const sahifa = oqi("web/src/app/(ichki)/kuzatuv/[symbol]/page.tsx");
  assert.ok(
    sahifa.includes('coin.segmentlar.find((s) => s.nom === "zona_konfluensiya")'),
    "timeframe segmentdan olinmagan",
  );
});
