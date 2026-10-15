import Link from "next/link";

import { HolatKarta } from "@/components/radar/HolatKarta";
import { Kalibrovka } from "@/components/radar/Kalibrovka";
import { type Tarjimon, vaqtMatni } from "@/components/radar/matn";
import { NomzodKartochka } from "@/components/radar/NomzodKartochka";
import { OynaTanlov, ReytingGrafigi } from "@/components/radar/ReytingGrafigi";
import { SessiyaJadvali } from "@/components/radar/SessiyaJadvali";
import { type SozlamaQatori, Sozlamalar } from "@/components/radar/Sozlamalar";
import { YashirinCoinlar } from "@/components/radar/YashirinCoinlar";
import { Card, CardTitle } from "@/components/ui/Card";
import { Ikonka } from "@/components/ui/Ikonka";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { sozlama } from "@/lib/config";
import { tarjimon } from "@/lib/i18n";
import {
  type Jadval,
  type Natija,
  SOZLAMA_KALITLARI,
  SOZLAMA_STANDART,
  STANDART_JADVAL,
  boshlanishdanKeyin,
  STANDART_ZONA,
  type SozlamaKalit,
  bugungiKun,
  joriyBolimlar,
  joriyKun,
  kalibrovka,
  keyingiSessiyalar,
  kunQosh,
  kunUstunlari,
  kunYaroqli,
  kunlarQatori,
  oraliqmi,
  oylikBump,
  oynaKunlari,
  sessiyaBump,
  sessiyaJadvali,
  sessiyaUstunlari,
  shablon,
  zonaniTekshir,
} from "@/lib/radar";
import {
  birinchiRasmiySlot,
  engSonggiSessiya,
  kalibrQatorlari,
  oldingiRasmiySessiyaId,
  oxirgiSessiya,
  radarHolati,
  radarTayyorligi,
  rasmiySessiyalar,
  sessiyaNatijalari,
  sozlamaOverridelari,
  yashirinlar,
  yengilNatijalar,
} from "@/lib/radar-baza";
import { kirim } from "@/lib/session";
import { hozir } from "@/lib/vaqt";

import { coinOch, coinYashir, sozlamaSaqla, sozlamaTikla } from "./amallar";
import { TekshirTugmasi } from "./TekshirTugmasi";

export const dynamic = "force-dynamic";

/** Calibration oynasi (kun). Sahifa butun tarixni har safar o'qimasin. */
const KALIBR_KUNLAR = 60;

/** Bitta qiymat yoki massiv bo'lib kelishi mumkin (`?kun=a&kun=b`). */
function bitta(x: string | string[] | undefined): string | undefined {
  return Array.isArray(x) ? x[0] : x;
}

function yamlSoni(kalitlar: string[], zaxira: number): number {
  const x = Number(sozlama(kalitlar, zaxira));
  return Number.isFinite(x) ? x : zaxira;
}

/** Modul 4.0.0 — "Portlash xavfi radari". FAQAT ADMIN.
 *
 * Yagona manba — `docs/MODUL_4_0_0.md`. Sahifa FAQAT O'QIYDI va
 * ko'rsatadi: hisob botda (`core/portlash_radari/`). Saytdan faqat
 * uchta narsa yoziladi — "hozir tekshir" bayrog'i, chegaralar va
 * yashirin coinlar (`amallar.ts`).
 *
 * QAT'IY CHEGARA: bu sahifa SIGNAL BERMAYDI. Kirish, stop yoki nishon
 * narxi yo'q, "sotib ol"/"sot" yo'q. Narx — "o'sha sessiyadagi narx".
 * Sahifa buni eng tepada ochiq yozadi.
 *
 * RASMIY = B. Grafik, sessiya jadvali va calibration FAQAT tasdiq (B)
 * sessiyalaridan quriladi. Qo'lda tekshiruv faqat "oxirgi qo'lda
 * tekshiruv" sifatida, so'ralganda ko'rinadi.
 *
 * Holat URL da: `?kun=YYYY-MM-DD&oraliq=1k|3k|1o&bolim=qolda`. Har
 * biri tekshiriladi — noto'g'ri qiymat standartga qaytadi.
 */
export default async function Modul4Sahifasi({
  searchParams,
}: {
  searchParams: Promise<{
    kun?: string | string[];
    oraliq?: string | string[];
    bolim?: string | string[];
  }>;
}) {
  const { admin, til } = await kirim();
  const t: Tarjimon = tarjimon(til);

  // Admin bo'lmaganga hech narsa so'ralmaydi — ma'lumot serverda ham
  // yuklanmaydi (`kuzatuv` sahifasi bilan bir xil qoida).
  if (!admin) {
    return (
      <>
        <Sarlavha matn={t("radar.sarlavha")} belgi="korish" />
        <Card>
          <p className="text-past text-sm">{t("admin.faqat_admin")}</p>
        </Card>
      </>
    );
  }

  const sorov = await searchParams;
  const hozirgi = await hozir();
  const zona = zonaniTekshir(sozlama(["radar", "vaqt_zonasi"], STANDART_ZONA));
  const jadval: Jadval = {
    kashfiyotDaqiqa: yamlSoni(["radar", "kashfiyot_daqiqa"], STANDART_JADVAL.kashfiyotDaqiqa),
    tasdiqDaqiqa: yamlSoni(["radar", "tasdiq_daqiqa"], STANDART_JADVAL.tasdiqDaqiqa),
    tasdiqKechikishDaqiqa: yamlSoni(
      ["radar", "tasdiq_kechikish_daqiqa"],
      STANDART_JADVAL.tasdiqKechikishDaqiqa,
    ),
  };
  const keyingi = keyingiSessiyalar(hozirgi, jadval);

  const tepa = (
    <>
      <Sarlavha matn={t("radar.sarlavha")} izoh={t("radar.izoh")} belgi="korish" />
      <Card variant="urgu" className="border-ortacha mb-4">
        <p className="text-ortacha flex items-start gap-2 text-sm">
          <Ikonka nom="ogohlantirish" className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <strong>{t("radar.ogoh_sarlavha")}.</strong> {t("radar.ogoh_matn")}
          </span>
        </p>
      </Card>
    </>
  );

  // Eski baza: migratsiya hali o'tmagan — yiqilmaymiz, tushuntiramiz.
  const tayyorlik = radarTayyorligi();
  if (!tayyorlik.tayyor) {
    return (
      <>
        {tepa}
        <Card>
          <CardTitle>{t("radar.bosh_sarlavha")}</CardTitle>
          <p className="text-matn-past mt-2 text-sm">
            {tayyorlik.sabab === "baza_yoq" ? t("radar.baza_yoq") : t("radar.jadval_yoq")}
          </p>
          <p className="text-matn-past mt-2 text-xs">
            {t("radar.keyingi_b")}: {vaqtMatni(t, keyingi.tasdiq, zona)}
          </p>
        </Card>
      </>
    );
  }

  // ---- Bazadan o'qish ------------------------------------------------
  const holati = radarHolati();
  const oxirgi = oxirgiSessiya("tasdiq");
  const qolda = oxirgiSessiya("qolda");
  const songgi = engSonggiSessiya();
  const overridelar = sozlamaOverridelari();

  /** Hozir kuchdagi chegara: admin qiymati, bo'lmasa YAML standarti. */
  const yamlStandart = (k: SozlamaKalit) => yamlSoni(["radar", k], SOZLAMA_STANDART[k]);
  const samarali = (k: SozlamaKalit) => overridelar.get(k)?.qiymat ?? yamlStandart(k);

  // Grafik va jadval oxirgi sessiya QAYSI Top-N bilan hisoblanganini
  // ko'rsatadi; sessiya bo'lmasa — hozirgi sozlama.
  const topN = Math.round(oxirgi?.sozlama.top_n ?? samarali("top_n"));
  const nomzodMin = Math.round(oxirgi?.sozlama.nomzod_min ?? samarali("nomzod_min"));

  // ---- Kun va oyna --------------------------------------------------
  const bugun = bugungiKun(hozirgi, jadval);
  const standartKun = joriyKun(oxirgi?.kun ?? null, hozirgi, jadval);
  const kunlar = kunlarQatori(standartKun > bugun ? standartKun : bugun);
  const kunXom = bitta(sorov.kun);
  const kun = kunYaroqli(kunXom) && kunlar.includes(kunXom) ? kunXom : standartKun;
  const oraliqXom = bitta(sorov.oraliq);
  const oraliq = oraliqmi(oraliqXom) ? oraliqXom : "1k";
  const oyna = oynaKunlari(kun, oraliq);

  const sessiyalar = rasmiySessiyalar(oyna[0], oyna[oyna.length - 1]);
  const oylik = oraliq === "1o";

  // Jadval: 1 oylik oynada 180 ta ustun o'qib bo'lmaydi — jadval
  // tanlangan kun uchun chiziladi (grafik esa butun oy).
  const birinchi = birinchiRasmiySlot();
  const jadvalUstunlari = boshlanishdanKeyin(
    sessiyaUstunlari(
      oylik ? [kun] : oyna,
      oylik ? sessiyalar.filter((s) => s.kun === kun) : sessiyalar,
      hozirgi,
      jadval,
    ),
    birinchi,
  );
  const grafikUstunlari = oylik
    ? boshlanishdanKeyin(kunUstunlari(oyna, sessiyalar, hozirgi, jadval), birinchi)
    : jadvalUstunlari;
  const oldingiId = oldingiRasmiySessiyaId(oylik ? kun : oyna[0]);
  const tugaganIdlar = sessiyalar.filter((s) => s.holat === "tugadi").map((s) => s.id);
  const natijalar = yengilNatijalar(oldingiId === null ? tugaganIdlar : [...tugaganIdlar, oldingiId]);

  const seriyalar = oylik
    ? oylikBump(grafikUstunlari, sessiyalar, natijalar, topN)
    : sessiyaBump(grafikUstunlari, natijalar, topN);
  const jadvalQatorlari = sessiyaJadvali(jadvalUstunlari, natijalar, oldingiId, topN);

  // ---- Joriy natijalar ------------------------------------------------
  // Qo'lda tekshiruv rasmiy sessiyadan YANGIROQ bo'lsagina eslatiladi.
  const qoldaYangi =
    qolda !== null &&
    (oxirgi === null ||
      (qolda.boshlandi?.getTime() ?? 0) > (oxirgi.boshlandi?.getTime() ?? 0));
  const qoldaKorinsin = qoldaYangi && bitta(sorov.bolim) === "qolda";
  const korsatilgan = qoldaKorinsin ? qolda : oxirgi;
  const joriy: Natija[] = korsatilgan ? sessiyaNatijalari(korsatilgan.id) : [];
  const bolimlar = joriyBolimlar(joriy);

  // ---- Calibration, sozlamalar, yashirinlar -----------------------------
  const kalibr = kalibrovka(kalibrQatorlari(kunQosh(bugun, -KALIBR_KUNLAR)), {
    portlash24: samarali("portlash_24s_pct"),
    portlash7: samarali("portlash_7k_pct"),
  });
  const sozlamaQatorlari: SozlamaQatori[] = SOZLAMA_KALITLARI.map((k) => ({
    kalit: k,
    joriy: samarali(k),
    standart: yamlStandart(k),
    ozgartirilgan: overridelar.has(k),
    sessiyada: oxirgi?.sozlama[k],
  }));
  const yashirin = yashirinlar();

  const havola = (bolim: string | null) =>
    `/modul-4?kun=${kun}&oraliq=${oraliq}${bolim ? `&bolim=${bolim}` : ""}#joriy`;

  return (
    <>
      {tepa}

      <nav className="mb-4 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {[
          ["joriy", t("radar.joriy_sarlavha")],
          ["grafik", t("radar.grafik_sarlavha")],
          ["jadval", t("radar.jadval_sarlavha")],
          ["kalibrovka", t("radar.kalibr_sarlavha")],
          ["sozlamalar", t("radar.sozlama_sarlavha")],
          ["yashirin", t("radar.yashirin_sarlavha")],
        ].map(([id, nom]) => (
          <a key={id} href={`#${id}`} className="text-matn-past hover:text-sarlavha underline-offset-4 hover:underline">
            {nom}
          </a>
        ))}
      </nav>

      <HolatKarta
        holati={holati}
        hozir={hozirgi}
        oxirgi={oxirgi}
        songgi={songgi}
        keyingi={keyingi}
        zona={zona}
        t={t}
        tugma={
          <TekshirTugmasi
            matn={t("radar.hozir_tekshir")}
            soraldi={t("radar.soraldi")}
            izoh={t("radar.tekshir_izoh")}
            soralgan={holati.sorov}
          />
        }
      />

      {/* ---- Joriy natijalar ---- */}
      <section id="joriy" className="mb-8 scroll-mt-20">
        <h2 className="text-sarlavha mb-1 text-lg font-semibold">{t("radar.joriy_sarlavha")}</h2>
        {korsatilgan === null ? (
          <Card>
            <p className="text-matn text-sm font-semibold">{t("radar.bosh_sarlavha")}</p>
            <p className="text-matn-past mt-1.5 text-sm">
              {shablon(t("radar.bosh_matn"), { v: vaqtMatni(t, keyingi.tasdiq, zona) })}
            </p>
          </Card>
        ) : (
          <>
            <p className="text-matn-past mb-2 text-xs">
              {qoldaKorinsin
                ? shablon(t("radar.qolda_korinmoqda"), { v: vaqtMatni(t, korsatilgan.boshlandi, zona) })
                : shablon(t("radar.joriy_izoh"), { v: vaqtMatni(t, korsatilgan.boshlandi, zona) })}
            </p>
            {qoldaYangi && qolda ? (
              <p className="border-ramka-yumshoq rounded-kichik mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 border px-3 py-2 text-xs">
                {qoldaKorinsin ? null : (
                  <span className="text-matn-past">
                    {shablon(t("radar.qolda_bor"), { v: vaqtMatni(t, qolda.boshlandi, zona) })}
                  </span>
                )}
                <Link
                  href={havola(qoldaKorinsin ? null : "qolda")}
                  className="text-sarlavha font-semibold hover:underline"
                >
                  {qoldaKorinsin ? t("radar.rasmiyga_qayt") : t("radar.qolda_kor")} →
                </Link>
              </p>
            ) : null}

            <Bolim
              sarlavha={t("radar.tasdiqlangan")}
              izoh={t("radar.tasdiqlangan_izoh")}
              ikonka="tasdiq"
              soni={bolimlar.tasdiqlangan.length}
              urgu
            >
              {bolimlar.tasdiqlangan.map((n) => (
                <NomzodKartochka key={n.symbol} natija={n} t={t} ochiq />
              ))}
            </Bolim>
            <Bolim
              sarlavha={t("radar.nomzodlar")}
              izoh={shablon(t("radar.nomzodlar_izoh"), { n: nomzodMin })}
              ikonka="korish"
              soni={bolimlar.nomzodlar.length}
            >
              {bolimlar.nomzodlar.map((n) => (
                <NomzodKartochka key={n.symbol} natija={n} t={t} />
              ))}
            </Bolim>
            {bolimlar.tasdiqlangan.length === 0 && bolimlar.nomzodlar.length === 0 ? (
              <Card className="mb-4">
                <p className="text-matn-past text-sm">{t("radar.nomzod_yoq")}</p>
              </Card>
            ) : null}
            <Bolim
              sarlavha={t("radar.otkinchi")}
              izoh={t("radar.otkinchi_izoh")}
              ikonka="kutilmoqda"
              soni={bolimlar.otkinchi.length}
            >
              {bolimlar.otkinchi.map((n) => (
                <NomzodKartochka key={n.symbol} natija={n} t={t} />
              ))}
            </Bolim>
            {bolimlar.boshqalar.length > 0 ? (
              <details className="group">
                <summary className="text-matn-past hover:text-sarlavha flex cursor-pointer list-none items-center gap-2 text-sm font-semibold select-none">
                  <Ikonka nom="pastga" className="h-4 w-4 transition-transform group-open:rotate-180" />
                  {t("radar.boshqalar")}
                  <span className="font-normal">({bolimlar.boshqalar.length})</span>
                </summary>
                <div className="mt-3 space-y-2">
                  {bolimlar.boshqalar.map((n) => (
                    <NomzodKartochka key={n.symbol} natija={n} t={t} />
                  ))}
                </div>
              </details>
            ) : null}
          </>
        )}
      </section>

      {/* ---- Grafik ---- */}
      <section id="grafik" className="mb-8 scroll-mt-20">
        <Card>
          <CardTitle className="mb-1">{t("radar.grafik_sarlavha")}</CardTitle>
          <p className="text-matn-past mb-3 text-xs">
            {shablon(t(oylik ? "radar.oylik_izoh" : "radar.grafik_izoh"), { n: topN })}
          </p>
          <OynaTanlov oraliq={oraliq} kun={kun} kunlar={kunlar} bugun={bugun} t={t} />
          <div className="mt-4">
            {grafikUstunlari.every((u) => u.holat !== "bor") ? (
              <p className="text-matn-past text-sm">{t("radar.grafik_bosh")}</p>
            ) : seriyalar.length === 0 ? (
              <p className="text-matn-past text-sm">
                {shablon(t("radar.grafik_hech"), { n: topN })}
              </p>
            ) : (
              <ReytingGrafigi
                seriyalar={seriyalar}
                ustunlar={grafikUstunlari}
                topN={topN}
                zona={zona}
                t={t}
                sanaKerak={oraliq === "3k"}
              />
            )}
          </div>
        </Card>
      </section>

      {/* ---- Sessiya jadvali ---- */}
      <section id="jadval" className="mb-8 scroll-mt-20">
        <Card>
          <CardTitle className="mb-1">{t("radar.jadval_sarlavha")}</CardTitle>
          {oylik ? <p className="text-matn-past mb-2 text-xs">{t("radar.jadval_oylik")}</p> : null}
          <div className="mt-2">
            <SessiyaJadvali
              qatorlar={jadvalQatorlari}
              ustunlar={jadvalUstunlari}
              zona={zona}
              t={t}
              sanaKerak={oraliq === "3k"}
            />
          </div>
          <p className="text-matn-past mt-3 text-[11px] leading-relaxed">{t("radar.jadval_izoh")}</p>
          <p className="text-matn-past mt-1 text-[11px] leading-relaxed">{t("radar.jadval_belgilar")}</p>
        </Card>
      </section>

      {/* ---- Calibration ---- */}
      <section id="kalibrovka" className="mb-8 scroll-mt-20">
        <Card>
          <CardTitle className="mb-2">{t("radar.kalibr_sarlavha")}</CardTitle>
          <Kalibrovka
            hisob={kalibr}
            t={t}
            portlash24={samarali("portlash_24s_pct")}
            portlash7={samarali("portlash_7k_pct")}
            kunlar={KALIBR_KUNLAR}
          />
        </Card>
      </section>

      {/* ---- Sozlamalar ---- */}
      <section id="sozlamalar" className="mb-8 scroll-mt-20">
        <Card>
          <CardTitle className="mb-1">{t("radar.sozlama_sarlavha")}</CardTitle>
          <p className="text-matn-past mb-4 text-xs">{t("radar.sozlama_izoh")}</p>
          <Sozlamalar qatorlar={sozlamaQatorlari} saqla={sozlamaSaqla} tikla={sozlamaTikla} t={t} />
        </Card>
      </section>

      {/* ---- Yashirin coinlar ---- */}
      <section id="yashirin" className="mb-8 scroll-mt-20">
        <Card>
          <CardTitle className="mb-1">{t("radar.yashirin_sarlavha")}</CardTitle>
          <p className="text-matn-past mb-4 text-xs">{t("radar.yashirin_izoh")}</p>
          <YashirinCoinlar
            royxat={yashirin}
            hozir={hozirgi}
            zona={zona}
            yashir={coinYashir}
            och={coinOch}
            t={t}
          />
        </Card>
      </section>

      <p className="text-matn-past mt-6 text-xs">{t("radar.xulosa_oxiri")}</p>
    </>
  );
}

/** Joriy natijalardagi bitta bo'lim. Bo'sh bo'lsa umuman chizilmaydi —
 *  "Tasdiqlangan (0)" sarlavhasi shovqin. */
function Bolim({
  sarlavha,
  izoh,
  ikonka,
  soni,
  urgu = false,
  children,
}: {
  sarlavha: string;
  izoh: string;
  ikonka: "tasdiq" | "korish" | "kutilmoqda";
  soni: number;
  urgu?: boolean;
  children: React.ReactNode;
}) {
  if (soni === 0) return null;
  return (
    <div className="mb-5">
      <h3
        className={
          urgu
            ? "text-sarlavha mb-1 flex items-center gap-2 text-sm font-semibold"
            : "text-matn mb-1 flex items-center gap-2 text-sm font-semibold"
        }
      >
        <Ikonka nom={ikonka} className={urgu ? "text-yaxshi h-4 w-4" : "text-matn-past h-4 w-4"} />
        {sarlavha}
        <span className="text-matn-past font-normal">({soni})</span>
      </h3>
      <p className="text-matn-past mb-2 text-xs">{izoh}</p>
      <div className="space-y-2">{children}</div>
    </div>
  );
}
