import { foizRangi, qisqaSon } from "@/lib/bozor";
import type { GlobalHolat } from "@/lib/bozor-server";
import { cn } from "@/lib/cn";

/** Sahifa tepasidagi global ko'rsatkichlar qatori.
 *
 * NEGA BU QATOR BOR. Har bir kripto saytining eng tepasida shunday
 * ingichka qator turadi: jami kapital, 24 soatlik hajm, BTC ulushi.
 * Foydalanuvchi uni boshqa saytlardan taniydi va sahifaga
 * "kripto sayti" tusini beradigan birinchi belgi aynan shu.
 *
 * IKKI XIL RAQAM YONMA-YON. Chapdagilar BUTUN BOZORDAN, o'ngdagi —
 * BIZNING 80 talik halol ro'yxatimizdan. Ular boshqa-boshqa narsalar
 * va shuning uchun har birining tagida nimadan olingani yozilgan.
 * Bittasini ikkinchisining o'rniga ko'rsatish aldash bo'lardi.
 */
export function BozorTepasi({
  global,
  halolKapital,
  halolSoni,
  jamiSoni,
  yorliq,
}: {
  global: GlobalHolat | null;
  halolKapital: number;
  halolSoni: number;
  jamiSoni: number;
  yorliq: {
    jami_kapital: string;
    hajm24: string;
    btc_ulushi: string;
    halol_kapital: string;
    bozor_manba: string;
    halol_manba: string;
  };
}) {
  return (
    <div className="border-ramka-yumshoq rounded-kartochka mb-5 grid grid-cols-2 gap-x-4 gap-y-3 border bg-white/[0.02] px-4 py-3 sm:grid-cols-4">
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
        matn={
          global?.btcUlushi === null || global?.btcUlushi === undefined
            ? "—"
            : `${global.btcUlushi.toFixed(1)}%`
        }
        manba={yorliq.bozor_manba}
      />
      <Katak
        nom={yorliq.halol_kapital}
        qiymat={halolKapital > 0 ? halolKapital : null}
        matn={halolKapital > 0 ? undefined : "—"}
        manba={`${yorliq.halol_manba} · ${halolSoni}/${jamiSoni}`}
      />
    </div>
  );
}

function Katak({
  nom,
  qiymat,
  matn,
  foiz,
  manba,
}: {
  nom: string;
  qiymat?: number | null;
  matn?: string;
  foiz?: number | null;
  manba: string;
}) {
  const korsatiladigan =
    matn ?? (qiymat === null || qiymat === undefined ? "—" : `$${qisqaSon(qiymat)}`);

  return (
    <div className="min-w-0">
      <p className="text-matn-past text-[11px] tracking-wide uppercase">{nom}</p>
      <p className="mt-0.5 flex items-baseline gap-1.5">
        <span className="raqam text-sarlavha font-semibold">
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
      </p>
      {/* Raqam qayerdan kelgani HAR DOIM yoziladi: sahifada butun
          bozor va bizning halol doiramiz yonma-yon turadi va ularni
          adashtirish oson. */}
      <p className="text-matn-past mt-0.5 truncate text-[10px]">{manba}</p>
    </div>
  );
}
