import { Card } from "@/components/ui/Card";
import { type Til, tarjimon } from "@/lib/i18n";

/** Bozor Salomatligi shkalasi — Fear & Greed uslubida.
 *
 * Chapda to'yingan qizil (0), o'rtada sariq (50), o'ngda to'yingan
 * ko'k-yashil (100); rang o'tishi tekis gradient. Bitta strelka qiymatga
 * qarab yoy bo'ylab turadi.
 *
 * Muhim: bu yerda HECH NARSA HISOBLANMAYDI. Qiymat ham, band ham
 * (`high`/`mid`/`low`) `core/analysis/market_health/` da hisoblanib,
 * bazaga yozilgan. Sayt faqat ko'rsatadi — topshiriqning 5-bo'limi shuni
 * talab qiladi va bu "bitta manba" qoidasini saqlaydi.
 */

const MARKAZ_X = 100;
const MARKAZ_Y = 100;
const RADIUS = 80;

/** Yoy bo'ylab 0-100 qiymatning koordinatasi. */
function nuqta(qiymat: number, radius: number): { x: number; y: number } {
  const burchak = ((100 - Math.min(100, Math.max(0, qiymat))) / 100) * Math.PI;
  return {
    x: MARKAZ_X + radius * Math.cos(burchak),
    y: MARKAZ_Y - radius * Math.sin(burchak),
  };
}

const BAND_KALITI: Record<string, string> = {
  high: "salomatlik.yaxshi",
  mid: "salomatlik.ortacha",
  low: "salomatlik.past",
};

const BAND_BELGISI: Record<string, string> = { high: "🟢", mid: "🟡", low: "🔴" };

export function SalomatlikShkalasi({
  qiymat,
  band,
  bandlar,
  til,
}: {
  qiymat: number;
  band: string;
  /** Konfiguratsiyadagi chegaralar — shkalada belgi qo'yish uchun */
  bandlar: { high: number; mid: number };
  til: Til;
}) {
  const t = tarjimon(til);
  const uchi = nuqta(qiymat, RADIUS - 14);
  const asos = nuqta(qiymat, 8);

  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox="0 0 200 118"
        className="w-full max-w-sm"
        role="img"
        aria-label={`${t("salomatlik.sarlavha")}: ${qiymat.toFixed(0)} / 100`}
      >
        <defs>
          <linearGradient id="shkala" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--rang-past-toq)" />
            <stop offset="50%" stopColor="var(--rang-ortacha)" />
            <stop offset="100%" stopColor="var(--rang-yaxshi)" />
          </linearGradient>
        </defs>

        <path
          d={`M ${MARKAZ_X - RADIUS} ${MARKAZ_Y} A ${RADIUS} ${RADIUS} 0 0 1 ${MARKAZ_X + RADIUS} ${MARKAZ_Y}`}
          fill="none"
          stroke="url(#shkala)"
          strokeWidth="16"
          strokeLinecap="round"
        />

        {/* Botning chegaralari — foydalanuvchi "qayerdan boshlab signal
            beriladi" degan savolga javobni SHKALADA ko'rsin */}
        {[bandlar.mid, bandlar.high].map((chegara) => {
          const ichki = nuqta(chegara, RADIUS - 9);
          const tashqi = nuqta(chegara, RADIUS + 9);
          return (
            <line
              key={chegara}
              x1={ichki.x}
              y1={ichki.y}
              x2={tashqi.x}
              y2={tashqi.y}
              stroke="var(--rang-fon)"
              strokeWidth="2.5"
            />
          );
        })}

        {/* Strelka */}
        <line
          x1={asos.x}
          y1={asos.y}
          x2={uchi.x}
          y2={uchi.y}
          stroke="var(--rang-oq)"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx={MARKAZ_X} cy={MARKAZ_Y} r="6" fill="var(--rang-oq)" />

        <text
          x="20"
          y="114"
          className="fill-[var(--rang-matn-past)] text-[9px]"
          textAnchor="middle"
        >
          0
        </text>
        <text
          x="180"
          y="114"
          className="fill-[var(--rang-matn-past)] text-[9px]"
          textAnchor="middle"
        >
          100
        </text>
      </svg>

      <p className="raqam text-sarlavha -mt-2 text-3xl font-bold">
        {qiymat.toFixed(0)}
        <span className="text-matn-past text-lg font-normal">/100</span>
      </p>
      <p className="mt-1 text-sm font-medium">
        {BAND_BELGISI[band] ?? "⚪"} {t(BAND_KALITI[band] ?? "umumiy.yoq")}
      </p>
    </div>
  );
}

export function SalomatlikYoq({ til }: { til: Til }) {
  const t = tarjimon(til);
  return (
    <Card>
      <p className="text-matn-past text-sm">{t("salomatlik.yoq")}</p>
    </Card>
  );
}
