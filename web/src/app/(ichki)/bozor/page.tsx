import { Card, CardTitle } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { bozorPosti, type BozorAsbobi, type BozorPosti } from "@/lib/bozorKorinishi";
import { sana } from "@/lib/format";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

export const dynamic = "force-dynamic";

/** BOZOR KO'RINISHI — haftalik va kunlik qarash.
 *
 * LOYIHA EGASINING SHARTI: bu SIGNAL EMAS va signalga ta'sir qilmaydi.
 * Asosiy tahlil 4 soatlikda qoladi. Bu sahifa — hafta boshida "bu
 * haftada nima kutamiz" va har kuni "bugun bozor qay holatda" degan
 * qarash.
 *
 * Sahifa hech narsa hisoblamaydi: postni bot quradi va bazaga yozadi.
 */

const BELGI: Record<string, string> = { up: "▲", down: "▼", flat: "▬" };

const RANG: Record<string, string> = {
  up: "text-yashil",
  down: "text-qizil",
  flat: "text-matn-past",
};

function pulShakli(qiymat: number): string {
  if (qiymat >= 1_000_000_000) return `$${(qiymat / 1_000_000_000).toFixed(2)} mlrd`;
  if (qiymat >= 1_000_000) return `$${(qiymat / 1_000_000).toFixed(2)} mln`;
  return `$${qiymat.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

function Qator({ asbob }: { asbob: BozorAsbobi }) {
  const qiymat = asbob.ulush ? `${asbob.qiymat.toFixed(2)}%` : pulShakli(asbob.qiymat);

  return (
    <div className="border-chegara flex items-center justify-between gap-3 border-b py-2 last:border-0">
      <div className="min-w-0">
        <div className="font-medium">{asbob.kod}</div>
        <div className="text-matn-past truncate text-xs">{asbob.nom}</div>
      </div>
      <div className="text-right">
        <div className="tabular-nums">{qiymat}</div>
        <div className={`text-xs ${RANG[asbob.yonalish] ?? ""}`}>
          {BELGI[asbob.yonalish] ?? ""} {asbob.izoh}
        </div>
      </div>
    </div>
  );
}

function Post({ post, sarlavha }: { post: BozorPosti | null; sarlavha: string }) {
  if (!post) {
    return (
      <Card>
        <CardTitle>{sarlavha}</CardTitle>
        <p className="text-matn-past text-sm">
          Hali post yo&apos;q — birinchi qarash tayyorlanmoqda.
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <CardTitle>{sarlavha}</CardTitle>
      {post.sana && <p className="text-matn-past mb-3 text-xs">{sana(post.sana)}</p>}

      <div className="mb-4">
        {post.asboblar.map((a) => (
          <Qator key={a.kod} asbob={a} />
        ))}
      </div>

      <p className="mb-2 text-sm">{post.xulosa}</p>
      <p className="text-matn-past text-sm">{post.kutilma}</p>
    </Card>
  );
}

export default async function Bozor() {
  const { til } = await kirim();
  const t = tarjimon(til);

  const haftalik = bozorPosti("haftalik");
  const kunlik = bozorPosti("kunlik");

  return (
    <div className="space-y-4">
      <Sarlavha
        matn={t("menyu.bozor")}
        izoh="Haftalik va kunlik qarash. Bu signal emas — signallar alohida bo'limda."
      />

      <Post post={haftalik} sarlavha="Haftalik qarash" />
      <Post post={kunlik} sarlavha="Kunlik qarash" />

      <Card>
        <CardTitle>Bu sahifa nima uchun</CardTitle>
        <p className="text-matn-past text-sm">
          Haftalik va kunlik grafiklar umumiy manzarani ko&apos;rsatadi: BTC, ETH,
          ustunliklar va bozor kapitalizatsiyasining kesimlari. Signal tahlili esa
          4 soatlik grafikda qilinadi va bu sahifaga bog&apos;liq emas.
        </p>
      </Card>
    </div>
  );
}
