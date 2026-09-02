import { JonliNarx } from "@/components/JonliNarx";
import { Card } from "@/components/ui/Card";
import { foiz, narx, sana } from "@/lib/format";
import { birjaJuftligi } from "@/lib/kalkulyator";

/** Signal kartochkasi — BOTDAGI SHABLONNING AYNAN O'ZI.
 *
 * NEGA MUHIM: foydalanuvchi bitta signalni ikki joyda ko'radi —
 * Telegramda va saytda. Ikkalasi boshqa-boshqa ko'rinishda bo'lsa,
 * u ularni solishtirishga urinadi va "qaysi biri to'g'ri?" degan savol
 * tug'iladi. Shuning uchun tartib, belgilar va nomlar bir xil:
 *
 *     💠 Kirish
 *     🛑 Stop      −4.55%
 *     🎯 TP1       +5.59%   50%
 *     🎯 TP2       +6.83%   50%
 *
 * TP SONI QAT'IY EMAS — 1, 2 yoki 3 bo'lishi mumkin. Kartochka
 * ro'yxatni o'zi bo'ylab yuradi: ilgari bu yerda aynan ikkita qator
 * yozib qo'yilgan edi va uchinchi TP jimgina ko'rinmay qolardi.
 *
 * Botdagi nusxasi: `bot/formatting.py` -> `render_levels()`.
 *
 * Saytda kalkulyator SHU KARTOCHKADAN KEYIN turadi — avval signalning
 * o'zi ko'rinsin, keyin u bilan nima qilish mumkinligi. Avval teskari
 * edi: sahifa avtomatik to'lgan kalkulyator maydonlaridan boshlanardi
 * va qaysi raqam signalniki ekani bilinmasdi.
 */
export function SignalKartochka({
  symbol,
  kotirovka,
  entry,
  stop,
  tplar,
  ulushlar,
  buyurtmaMatni,
  berilgan,
  matnlar,
}: {
  symbol: string;
  kotirovka: string;
  entry: number;
  stop: number;
  /** TP narxlari — 1 tadan 3 tagacha, pastdan yuqoriga */
  tplar: number[];
  /** Har bir TP da sotiladigan ulush — konfiguratsiyadan */
  ulushlar: number[];
  /** "Buyurtma qoldiring…" yoki "Hozir oling…" — belgisi bilan */
  buyurtmaMatni: string;
  berilgan: Date | null;
  matnlar: Record<string, string>;
}) {
  const oz = (narxi: number) => ((narxi - entry) / entry) * 100;
  // Nisbat YAKUNIY nishon bo'yicha — TP nechta bo'lishidan qat'i nazar.
  const yakuniy = tplar[tplar.length - 1];
  const nisbat = entry > stop ? (yakuniy - entry) / (entry - stop) : null;

  return (
    <Card variant="urgu">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-sarlavha raqam text-lg font-bold">
          {symbol}/{kotirovka}
        </span>
        <span className="text-matn-past text-xs">{buyurtmaMatni}</span>
      </div>

      <div className="border-ramka/50 mt-3 space-y-1.5 border-t border-b py-3">
        <Qator belgi="💠" nom={matnlar.kirish} qiymat={narx(entry)} />
        <Qator
          belgi="🛑"
          nom={matnlar.stop}
          qiymat={narx(stop)}
          ozgarish={oz(stop)}
          tone="past"
        />
        {tplar.map((tp, i) => (
          <Qator
            key={`tp${i + 1}`}
            belgi="🎯"
            nom={`TP${i + 1}`}
            qiymat={narx(tp)}
            ozgarish={oz(tp)}
            ulush={ulushlar[i]}
            tone="yaxshi"
          />
        ))}
      </div>

      {/* HOZIRGI narx — faqat saytda. Telegram xabari bir marta
          yuboriladi va o'zgarmaydi, sayt esa jonli ko'rsata oladi. */}
      <dl className="mt-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <dt className="text-matn-past text-xs uppercase">📊 {matnlar.hozir}</dt>
        <dd>
          <JonliNarx juftlik={birjaJuftligi(symbol, kotirovka)} kirish={entry} />
        </dd>
      </dl>

      <dl className="mt-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <dt className="text-matn-past text-xs uppercase">⚖️ {matnlar.nisbat}</dt>
        <dd className="raqam text-sarlavha font-semibold">
          {nisbat === null ? "—" : `1 : ${nisbat.toFixed(2)}`}
        </dd>
      </dl>

      <p className="text-matn-past mt-3 text-xs leading-relaxed">
        🔸 {matnlar.stop_izoh}
      </p>
      <p className="text-matn-past raqam mt-1 text-xs">
        🗓 {sana(berilgan)} UTC
      </p>
    </Card>
  );
}

function Qator({
  belgi,
  nom,
  qiymat,
  ozgarish,
  ulush,
  tone,
}: {
  belgi: string;
  nom: string;
  qiymat: string;
  ozgarish?: number;
  ulush?: number;
  tone?: "past" | "yaxshi";
}) {
  const rang = tone === "past" ? "text-past" : tone === "yaxshi" ? "text-yaxshi" : "";
  return (
    <div className="flex items-baseline gap-2 text-sm">
      <span aria-hidden>{belgi}</span>
      <span className="text-matn-past w-14 shrink-0">{nom}</span>
      {/* Narx o'ngga tekislanadi: to'rt qator bir ustunda tursin —
          botdagi monoshirift blok bilan bir xil o'qiladi. */}
      <span className={`raqam flex-1 text-right font-semibold ${rang}`}>{qiymat}</span>
      <span className={`raqam w-16 shrink-0 text-right text-xs ${rang}`}>
        {ozgarish === undefined ? "" : foiz(ozgarish)}
      </span>
      <span className="text-matn-past raqam w-10 shrink-0 text-right text-xs">
        {ulush === undefined ? "" : `${ulush}%`}
      </span>
    </div>
  );
}
