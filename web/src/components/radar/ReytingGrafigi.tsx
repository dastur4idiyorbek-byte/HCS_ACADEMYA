import Link from "next/link";

import { cn } from "@/lib/cn";
import {
  type BumpNuqta,
  type BumpSeriya,
  ORALIQLAR,
  type Oraliq,
  type Ustun,
  seriyaUslubi,
  shablon,
} from "@/lib/radar";

import { type Tarjimon, kunYorligi, ustunYorligi } from "./matn";

/** O'rin oqimi — bump chart, sof SVG, SERVERDA chiziladi (10-bo'lim).
 *
 * NEGA KUTUBXONASIZ. Grafik statik: ma'lumot sahifa ochilganda bir
 * marta keladi, interaktivlik — faqat nuqta ustidagi `<title>`. Buning
 * uchun mijozga yuzlab kilobayt JavaScript yuborish ortiqcha.
 *
 * TUZILISHI (yuqoridan pastga):
 *   1..N o'rinlar      — har coin o'z o'rnida, ustundan ustunga chiziq
 *   "Top-N dan tashqari" — pool ichida, lekin pastroq: nuqta yonida #13
 *   "chiqdi"            — oldingi ustunda bor edi, endi elakdan ham tushdi
 * O'tkazib yuborilgan sessiya ustuni bo'sh qoladi va chiziq UZILADI —
 * yo'q ma'lumotni chiziq bilan "to'ldirish" yolg'on bo'lardi.
 *
 * RANG YOLG'IZ QOLMAYDI: har chiziqning ikki uchida coin nomi yozilgan,
 * pastda legenda bor, 8 tadan keyin chiziq shakli o'zgaradi. Ranglar
 * `radar.ts/SERIYA_RANGLARI` da, bir marta tanlangan va tekshirilgan.
 *
 * TELEFON. SVG o'z kengligida chiziladi va `overflow-x-auto` ichida
 * suriladi — sahifaning o'zi hech qachon gorizontal surilmaydi.
 */

const QATOR = 26;
const BOSH_X = 108;
const ONG = 92;
const SARLAVHA = 44;
const QAVAT = 14;
const ORALIQ_BOSHLIQ = 18;

type Joy = { x: number; y: number };

export function ReytingGrafigi({
  seriyalar,
  ustunlar,
  topN,
  zona,
  t,
  sanaKerak,
}: {
  seriyalar: BumpSeriya[];
  ustunlar: Ustun[];
  topN: number;
  zona: string;
  t: Tarjimon;
  /** 3 kunlik oynada ustun sarlavhasiga sana ham yoziladi */
  sanaKerak: boolean;
}) {
  const oylik = ustunlar.some((u) => u.tartib === null);
  const ustunEni = oylik ? 46 : sanaKerak ? 76 : 72;
  const kenglik = BOSH_X + ustunlar.length * ustunEni + ONG;

  // Zonalardagi "qavat"lar: bitta ustunda bir nechta coin bo'lsa ular
  // ustma-ust tushmasin — tartib bilan pastga suriladi.
  const qavatlar = ustunlar.map(() => ({ tash: [] as string[], chiq: [] as string[] }));
  for (const s of seriyalar) {
    s.nuqtalar.forEach((n, i) => {
      if (n.tur === "tashqarida") qavatlar[i].tash.push(s.symbol);
      if (n.tur === "chiqdi") qavatlar[i].chiq.push(s.symbol);
    });
  }
  const orinXaritasi = new Map(seriyalar.map((s) => [s.symbol, s]));
  qavatlar.forEach((q, i) => {
    const orin = (sym: string) => {
      const n = orinXaritasi.get(sym)?.nuqtalar[i];
      return n && n.tur === "tashqarida" ? n.orin : Infinity;
    };
    q.tash.sort((a, b) => orin(a) - orin(b) || a.localeCompare(b));
    q.chiq.sort((a, b) => (orinXaritasi.get(a)?.tartib ?? 0) - (orinXaritasi.get(b)?.tartib ?? 0));
  });
  const engKopTash = Math.max(1, ...qavatlar.map((q) => q.tash.length));
  const engKopChiq = Math.max(1, ...qavatlar.map((q) => q.chiq.length));

  const topBoshi = SARLAVHA + 10;
  const topOxiri = topBoshi + topN * QATOR;
  const tashBoshi = topOxiri + ORALIQ_BOSHLIQ;
  const tashOxiri = tashBoshi + 10 + engKopTash * QAVAT;
  const chiqBoshi = tashOxiri + ORALIQ_BOSHLIQ;
  const chiqOxiri = chiqBoshi + 10 + engKopChiq * QAVAT;
  const balandlik = chiqOxiri + 8;

  const ustunX = (i: number) => BOSH_X + i * ustunEni + ustunEni / 2;

  const joyi = (s: BumpSeriya, n: BumpNuqta, i: number): Joy | null => {
    const x = ustunX(i);
    if (n.tur === "orin") return { x, y: topBoshi + (n.orin - 0.5) * QATOR };
    if (n.tur === "tashqarida") {
      return { x, y: tashBoshi + 5 + (qavatlar[i].tash.indexOf(s.symbol) + 0.5) * QAVAT };
    }
    if (n.tur === "chiqdi") {
      return { x, y: chiqBoshi + 5 + (qavatlar[i].chiq.indexOf(s.symbol) + 0.5) * QAVAT };
    }
    return null;
  };

  const ustunMatni = (u: Ustun) => {
    const y = ustunYorligi(t, u, zona, true);
    return y.ustki ? `${y.ustki} · ${y.asosiy}` : y.asosiy;
  };
  const tashqariNomi = shablon(t("radar.tashqarida"), { n: topN });

  return (
    <div>
      <div className="rounded-kichik border-ramka-yumshoq/60 overflow-x-auto border">
        <svg
          role="img"
          aria-label={t("radar.grafik_nomi")}
          width={kenglik}
          height={balandlik}
          viewBox={`0 0 ${kenglik} ${balandlik}`}
          className="group/bump block"
          style={{ background: "var(--rang-fon)" }}
        >
          {/* Zonalar foni — o'rinlardan ajralib tursin */}
          <rect
            x={BOSH_X}
            y={tashBoshi}
            width={ustunlar.length * ustunEni}
            height={tashOxiri - tashBoshi}
            fill="var(--rang-matn-past)"
            opacity={0.06}
            rx={6}
          />
          <rect
            x={BOSH_X}
            y={chiqBoshi}
            width={ustunlar.length * ustunEni}
            height={chiqOxiri - chiqBoshi}
            fill="var(--rang-past)"
            opacity={0.06}
            rx={6}
          />
          <text x={BOSH_X + 2} y={tashBoshi - 5} fontSize={10} fill="var(--rang-matn-past)">
            {tashqariNomi}
          </text>
          <text x={BOSH_X + 2} y={chiqBoshi - 5} fontSize={10} fill="var(--rang-matn-past)">
            {t("radar.chiqdi")}
          </text>

          {/* O'rin chiziqlari va raqamlari */}
          {Array.from({ length: topN }, (_, k) => {
            const y = topBoshi + (k + 0.5) * QATOR;
            return (
              <g key={k}>
                <line
                  x1={BOSH_X}
                  x2={kenglik - ONG}
                  y1={y}
                  y2={y}
                  stroke="var(--rang-matn-past)"
                  strokeOpacity={0.14}
                  strokeWidth={1}
                />
                <text
                  x={22}
                  y={y + 3.5}
                  fontSize={10}
                  textAnchor="end"
                  fill="var(--rang-matn-past)"
                  className="raqam"
                >
                  {k + 1}
                </text>
              </g>
            );
          })}

          {/* Ustun sarlavhalari; o'tkazib yuborilgan ustun — bo'sh, belgilangan */}
          {ustunlar.map((u, i) => {
            const y = ustunYorligi(t, u, zona, sanaKerak);
            const x = ustunX(i);
            const otkazildi = u.holat === "otkazildi";
            return (
              <g key={u.kalit}>
                {y.ustki ? (
                  <text x={x} y={16} fontSize={10} textAnchor="middle" fill="var(--rang-matn-past)">
                    {y.ustki}
                  </text>
                ) : null}
                <text
                  x={x}
                  y={y.ustki ? 30 : oylik ? 30 : 24}
                  fontSize={oylik ? 10 : 10.5}
                  textAnchor="middle"
                  fill={otkazildi ? "var(--rang-past)" : "var(--rang-matn)"}
                >
                  {y.nom}
                </text>
                {y.soat ? (
                  <text
                    x={x}
                    y={y.ustki ? 41 : 37}
                    fontSize={10}
                    textAnchor="middle"
                    fill="var(--rang-matn-past)"
                    className="raqam"
                  >
                    {y.soat}
                  </text>
                ) : null}
                {otkazildi ? (
                  <>
                    <rect
                      x={x - ustunEni / 2 + 3}
                      y={topBoshi - 4}
                      width={ustunEni - 6}
                      height={chiqOxiri - topBoshi + 4}
                      fill="var(--rang-past)"
                      opacity={0.07}
                      rx={4}
                    >
                      <title>{`${ustunMatni(u)} — ${t("radar.otkazildi")}`}</title>
                    </rect>
                    <text
                      transform={`translate(${x + 3.5} ${(topBoshi + topOxiri) / 2}) rotate(-90)`}
                      fontSize={10}
                      textAnchor="middle"
                      fill="var(--rang-past)"
                    >
                      {t("radar.otkazildi")}
                    </text>
                  </>
                ) : null}
              </g>
            );
          })}

          {/* Seriyalar. Ustiga borilganda qolganlari xiralashadi. */}
          {seriyalar.map((s) => {
            const { rang, chiziq } = seriyaUslubi(s.tartib);
            const joylar = s.nuqtalar.map((n, i) => joyi(s, n, i));
            const bolaklar: { a: Joy; b: Joy; xira: boolean }[] = [];
            for (let i = 1; i < joylar.length; i++) {
              const a = joylar[i - 1];
              const b = joylar[i];
              if (!a || !b) continue;
              const xira = s.nuqtalar[i].tur === "chiqdi" || s.nuqtalar[i - 1].tur === "chiqdi";
              bolaklar.push({ a, b, xira });
            }
            const korinadi = joylar
              .map((j, i) => ({ j, i }))
              .filter((x): x is { j: Joy; i: number } => x.j !== null);
            if (korinadi.length === 0) return null;
            const birinchi = korinadi[0];
            const oxirgi = korinadi[korinadi.length - 1];
            const yorliq = s.belgi || s.symbol;

            return (
              <g
                key={s.symbol}
                className="transition-opacity group-hover/bump:opacity-30 hover:opacity-100!"
              >
                {/* Ko'rinmas keng chiziq — ingichka chiziqni sichqoncha bilan
                    topish qiyin, ustiga borish maydoni kattaroq bo'lsin. */}
                {bolaklar.map((b, k) => (
                  <line
                    key={`h${k}`}
                    x1={b.a.x}
                    y1={b.a.y}
                    x2={b.b.x}
                    y2={b.b.y}
                    stroke="transparent"
                    strokeWidth={12}
                    pointerEvents="stroke"
                  />
                ))}
                {bolaklar.map((b, k) => (
                  <line
                    key={`c${k}`}
                    x1={b.a.x}
                    y1={b.a.y}
                    x2={b.b.x}
                    y2={b.b.y}
                    stroke={rang}
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeDasharray={chiziq}
                    strokeOpacity={b.xira ? 0.45 : 1}
                  />
                ))}
                {korinadi.map(({ j, i }) => {
                  const n = s.nuqtalar[i];
                  const holat =
                    n.tur === "orin" || n.tur === "tashqarida" ? `#${n.orin}` : t("radar.chiqdi");
                  return (
                    <g key={`n${i}`}>
                      <circle
                        cx={j.x}
                        cy={j.y}
                        r={n.tur === "chiqdi" ? 3.5 : 4}
                        fill={n.tur === "chiqdi" ? "var(--rang-fon)" : rang}
                        stroke={n.tur === "chiqdi" ? rang : "var(--rang-fon)"}
                        strokeWidth={n.tur === "chiqdi" ? 1.5 : 2}
                      >
                        <title>{`${s.symbol} — ${ustunMatni(ustunlar[i])} — ${holat}`}</title>
                      </circle>
                      {n.tur === "tashqarida" ? (
                        <text
                          x={j.x + 7}
                          y={j.y + 3.5}
                          fontSize={9.5}
                          fill="var(--rang-matn-past)"
                          className="raqam"
                        >
                          #{n.orin}
                        </text>
                      ) : null}
                    </g>
                  );
                })}
                {birinchi.i !== oxirgi.i ? (
                  <Yorliq x={birinchi.j.x - 9} y={birinchi.j.y} anchor="end" matn={yorliq} />
                ) : null}
                <Yorliq
                  x={oxirgi.j.x + (s.nuqtalar[oxirgi.i].tur === "tashqarida" ? 30 : 9)}
                  y={oxirgi.j.y}
                  anchor="start"
                  matn={yorliq}
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legenda — rangni ko'ra olmaydigan uchun ham: namuna chiziq + nom */}
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5" aria-label={t("radar.legenda")}>
        {seriyalar.map((s) => {
          const { rang, chiziq } = seriyaUslubi(s.tartib);
          return (
            <li key={s.symbol} className="text-matn flex items-center gap-1.5 text-xs">
              <svg width={22} height={8} aria-hidden className="shrink-0">
                <line
                  x1={1}
                  y1={4}
                  x2={21}
                  y2={4}
                  stroke={rang}
                  strokeWidth={2}
                  strokeDasharray={chiziq}
                  strokeLinecap="round"
                />
              </svg>
              {s.symbol}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Chiziq uchidagi nom. Atrofidagi fon rangli "halqa" boshqa chiziq
 *  ustidan o'tganda ham o'qilishini ta'minlaydi. Matn — matn rangida,
 *  seriya rangida EMAS (och rangli matn fonda o'qilmaydi). */
function Yorliq({
  x,
  y,
  anchor,
  matn,
}: {
  x: number;
  y: number;
  anchor: "start" | "end";
  matn: string;
}) {
  return (
    <text
      x={x}
      y={y + 3.5}
      fontSize={11}
      fontWeight={600}
      textAnchor={anchor}
      fill="var(--rang-matn)"
      stroke="var(--rang-fon)"
      strokeWidth={3}
      paintOrder="stroke"
      strokeLinejoin="round"
    >
      {matn}
    </text>
  );
}

/** Oyna tanlovi: [1 kun] [3 kun] [1 oy] va kunlar qatori.
 *
 * Hammasi oddiy havola (`?kun=...&oraliq=...`): holat URL da turadi,
 * sahifa serverda chiziladi — mijoz holati ham, JavaScript ham kerak
 * emas, havolani esa boshqa adminga yuborish mumkin.
 */
export function OynaTanlov({
  oraliq,
  kun,
  kunlar,
  bugun,
  t,
}: {
  oraliq: Oraliq;
  kun: string;
  /** Kunlar qatori — eng yangisi birinchi */
  kunlar: string[];
  bugun: string;
  t: Tarjimon;
}) {
  const havola = (k: string, o: Oraliq) => `/modul-4?kun=${k}&oraliq=${o}#grafik`;
  return (
    <div className="space-y-2.5">
      <nav aria-label={t("radar.oraliq_tanlash")} className="flex flex-wrap gap-2">
        {ORALIQLAR.map((o) => (
          <Link
            key={o}
            href={havola(kun, o)}
            aria-current={o === oraliq ? "page" : undefined}
            className={cn(
              "rounded-tugma border px-3 py-1.5 text-xs font-semibold transition-colors",
              o === oraliq
                ? "border-ramka bg-ramka text-[#0a2450]"
                : "border-ramka-yumshoq text-sarlavha hover:bg-panel-yorqin",
            )}
          >
            {t(`radar.oraliq.${o}`)}
          </Link>
        ))}
      </nav>
      <nav aria-label={t("radar.kunlar_qatori")} className="-mx-1 overflow-x-auto pb-1">
        <ul className="flex w-max gap-1 px-1">
          {kunlar.map((k) => (
            <li key={k}>
              <Link
                href={havola(k, oraliq)}
                aria-current={k === kun ? "date" : undefined}
                className={cn(
                  "block rounded-full border px-2.5 py-1 text-xs whitespace-nowrap transition-colors",
                  k === kun
                    ? "border-sarlavha text-sarlavha font-semibold"
                    : "text-matn-past hover:text-sarlavha border-transparent",
                )}
              >
                {kunYorligi(t, k, bugun)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
