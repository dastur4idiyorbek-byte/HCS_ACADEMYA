import { Doira } from "@/components/Doira";
import { foizRangi, qisqaSon } from "@/lib/bozor";
import type { GlobalHolat, QorquvIndeksi } from "@/lib/bozor-server";
import { cn } from "@/lib/cn";

/** Sahifaning tepasi: doira shkala + global ko'rsatkichlar.
 *
 * NEGA BIR PANELDA. Har bir kripto saytining tepasida shunday qator
 * turadi va foydalanuvchi uni tanib oladi. Bizda esa uning chap
 * yonida loyihaning O'Z ko'rsatkichi — Bozor Salomatligi — turadi.
 * Boshqa hech qaysi saytda u yo'q, shuning uchun eng ko'rinadigan
 * joyda turishi kerak.
 *
 * TAKROR YO'Q. Salomatlik raqami FAQAT shu yerda ko'rinadi. Pastdagi
 * kartochkada uning tafsiloti qoladi (nechta coin tekshirildi, qayerda
 * uzildi) — o'sha raqamning o'zi emas.
 *
 * IKKI XIL MANBA YONMA-YON, shuning uchun har birining tagida
 * nimadan olingani yozilgan: "butun bozor" va "halol ro'yxat"
 * boshqa-boshqa narsalar va ularni adashtirish oson.
 */
export function BozorTepasi({
  salomatlik,
  salomatlikTasnifi,
  global,
  qorquv,
  altcoin,
  halolKapital,
  halolSoni,
  jamiSoni,
  yorliq,
}: {
  salomatlik: number | null;
  salomatlikTasnifi?: string;
  global: GlobalHolat | null;
  qorquv: QorquvIndeksi | null;
  altcoin: number | null;
  halolKapital: number;
  halolSoni: number;
  jamiSoni: number;
  yorliq: {
    salomatlik: string;
    jami_kapital: string;
    hajm24: string;
    btc_ulushi: string;
    eth_ulushi: string;
    qorquv: string;
    altcoin: string;
    halol_kapital: string;
    bozor_manba: string;
    halol_manba: string;
  };
}) {
  return (
    <div className="rounded-kartochka oyna-yuza border-ramka mb-5 flex flex-col gap-5 border p-4 sm:flex-row sm:items-center sm:gap-6 sm:p-5">
      <div className="shrink-0 self-center">
        <Doira
          qiymat={salomatlik}
          tasnif={salomatlikTasnifi}
          sarlavha={yorliq.salomatlik}
        />
      </div>

      {/* Ko'rsatkichlar. Telefonda ikki ustun, kengroq ekranda uch —
          ular qisqa va yonma-yon o'qiladi. */}
      <div className="grid min-w-0 flex-1 grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
        <Katak
          nom={yorliq.jami_kapital}
          qiymat={global?.jamiKapital ?? null}
          foiz={global?.ozgarish24 ?? null}
          manba={yorliq.bozor_manba}
        />
        <Katak
          nom={yorliq.hajm24}
          qiymat={global?.hajm24 ?? null}
          manba={yorliq.bozor_manba}
        />
        <Katak
          nom={yorliq.btc_ulushi}
          matn={foizMatn(global?.btcUlushi)}
          manba={yorliq.bozor_manba}
        />
        <Katak
          nom={yorliq.eth_ulushi}
          matn={foizMatn(global?.ethUlushi)}
          manba={yorliq.bozor_manba}
        />
        <Katak
          nom={yorliq.qorquv}
          matn={qorquv === null ? "—" : String(qorquv.qiymat)}
          izoh={qorquv?.tasnif}
          manba={yorliq.bozor_manba}
        />
        <Katak
          nom={yorliq.altcoin}
          matn={altcoin === null ? "—" : String(altcoin)}
          // Bu ko'rsatkich BIZNING ro'yxatimiz bo'yicha hisoblanadi va
          // shuning uchun boshqa saytlardagidan farq qiladi. Manbasi
          // yozilmasa, farq "xato" bo'lib ko'rinardi.
          manba={yorliq.halol_manba}
        />
        <div className="col-span-2 sm:col-span-3">
          <Katak
            nom={yorliq.halol_kapital}
            qiymat={halolKapital > 0 ? halolKapital : null}
            manba={`${yorliq.halol_manba} · ${halolSoni}/${jamiSoni}`}
          />
        </div>
      </div>
    </div>
  );
}

function foizMatn(qiymat: number | null | undefined): string {
  return qiymat === null || qiymat === undefined ? "—" : `${qiymat.toFixed(1)}%`;
}

function Katak({
  nom,
  qiymat,
  matn,
  izoh,
  foiz,
  manba,
}: {
  nom: string;
  qiymat?: number | null;
  matn?: string;
  izoh?: string;
  foiz?: number | null;
  manba: string;
}) {
  const korsatiladigan =
    matn ??
    (qiymat === null || qiymat === undefined ? "—" : `$${qisqaSon(qiymat)}`);

  return (
    <div className="min-w-0">
      <p className="text-matn-past text-[11px] tracking-wide uppercase">{nom}</p>
      <p className="mt-0.5 flex flex-wrap items-baseline gap-x-1.5">
        <span className="raqam text-sarlavha text-lg leading-none font-semibold">
          {korsatiladigan}
        </span>
        {foiz !== undefined && foiz !== null && (
          <span
            className={cn(
              "raqam text-[11px]",
              foizRangi(foiz) === "yaxshi"
                ? "text-yaxshi"
                : foizRangi(foiz) === "past"
                  ? "text-past"
                  : "text-matn-past",
            )}
          >
            <span aria-hidden>{foiz > 0.1 ? "▲" : foiz < -0.1 ? "▼" : "•"}</span>
            {Math.abs(foiz).toFixed(2)}%
          </span>
        )}
        {izoh && <span className="text-matn-past text-[11px]">{izoh}</span>}
      </p>
      {/* Raqam qayerdan kelgani HAR DOIM yoziladi: sahifada butun bozor
          va bizning halol doiramiz yonma-yon turadi. */}
      <p className="text-matn-past mt-0.5 truncate text-[10px]">{manba}</p>
    </div>
  );
}
