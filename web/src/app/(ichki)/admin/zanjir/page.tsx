import { BlokZanjiri } from "@/components/BlokZanjiri";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { zanjirHolatlari } from "@/lib/queries";
import { kirim } from "@/lib/session";
import {
  salomatlikIndeksi,
  xulosaHisobla,
  type CoinZanjiri,
} from "@/lib/zanjir";

export const dynamic = "force-dynamic";

/** ⛓️ Jonli Blok Zanjiri — admin monitori (4-prompt, 3-qism).
 *
 * Eski "👨‍🍳 Jonli Oshxona" eski tahlil moduli bilan birga o'chirilgan
 * edi (`pipeline_events` jadvali ham). Bu — o'sha ekranning YANGI
 * modul uchun qayta qurilgani, promptdagi nom bilan.
 *
 * NIMA KO'RSATADI: har coin uchun to'rt blok — Fundamental, Struktura,
 * Zona sifati, Tasdiqlash — va zanjir qayerda uzilgani.
 *
 * BU JONLI OQIM EMAS. Sikl har necha soatda yuradi va bir necha
 * soniyada tugaydi. Ekran o'sha yugurishning YOZILGAN natijasini
 * qayta o'ynatadi. Sahifa tepasida oxirgi tekshiruv vaqti turadi —
 * "jonli" ko'rinib, aslida eski raqam ko'rsatadigan ekran eng yomon
 * turdagi interfeys bo'lardi.
 */
export default async function AdminZanjir() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const coinlar = zanjirHolatlari();
  const xulosa = xulosaHisobla(coinlar);
  const indeks = salomatlikIndeksi(xulosa);

  if (coinlar.length === 0) {
    return (
      <Card>
        <CardTitle>⛓️ {t("zanjir.sarlavha")}</CardTitle>
        <p className="text-matn-past mt-2 text-sm">{t("zanjir.hali_yoq")}</p>
        <CardHint className="mt-2">{t("zanjir.hali_yoq_izoh")}</CardHint>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card variant="urgu">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>⛓️ {t("zanjir.sarlavha")}</CardTitle>
          <Badge tone="neytral">{sana(xulosa.oxirgi)}</Badge>
        </div>

        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
          <Raqam nom={t("zanjir.tekshirildi")} qiymat={String(xulosa.jami)} />
          <Raqam nom={t("zanjir.toliq")} qiymat={String(xulosa.toliq)} />
          <Raqam nom={t("zanjir.signal")} qiymat={String(xulosa.signal)} />
          <Raqam
            nom={t("zanjir.ortacha")}
            qiymat={`${xulosa.ortachaBloklar.toFixed(1)} / 4`}
          />
        </dl>

        {indeks !== null && (
          <p className="text-matn-past mt-3 text-sm">
            {t("zanjir.indeks")}:{" "}
            <span className="raqam font-semibold">{indeks}</span>
            /100
          </p>
        )}
        {/* Bu ekran FAQAT kuzatadi. Undagi hech bir raqam modulga
            qaytib kirmaydi va signal qaroriga ta'sir qilmaydi. */}
        <CardHint className="mt-3">{t("zanjir.bir_tomonlama")}</CardHint>
      </Card>

      <div className="space-y-2">
        {coinlar.map((coin) => (
          <CoinQatori key={coin.symbol} coin={coin} t={t} />
        ))}
      </div>
    </div>
  );
}

function Raqam({ nom, qiymat }: { nom: string; qiymat: string }) {
  return (
    <div>
      <dt className="text-matn-past text-xs uppercase">{nom}</dt>
      <dd className="raqam text-sarlavha text-lg font-bold">{qiymat}</dd>
    </div>
  );
}

function CoinQatori({
  coin,
  t,
}: {
  coin: CoinZanjiri;
  t: (k: string) => string;
}) {
  const kutilmoqda = coin.bloklar.length === 0;

  return (
    <div
      className={
        "border-ramka-yumshoq bg-panel rounded-kartochka border p-3.5 " +
        (kutilmoqda ? "blok-kutilmoqda" : "")
      }
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-sarlavha font-semibold">{coin.symbol}</span>
        {coin.toliq && (
          <Badge tone="yaxshi">
            {t("zanjir.ishonch")} {(coin.ishonch * 100).toFixed(0)}%
          </Badge>
        )}
        {coin.uzildiBlokda && (
          <Badge tone="past">
            {t("zanjir.uzildi")}: {coin.uzildiBlokda}
          </Badge>
        )}
        {coin.signalId && <Badge tone="yaxshi">#{coin.signalId}</Badge>}
      </div>

      {kutilmoqda ? (
        <p className="text-matn-past text-sm">
          {coin.izoh || t("zanjir.tekshirilmagan")}
        </p>
      ) : (
        <BlokZanjiri coin={coin} />
      )}

      {coin.izoh && !kutilmoqda && (
        <p className="text-matn-past mt-2 text-xs">{coin.izoh}</p>
      )}
    </div>
  );
}
