import { cn } from "@/lib/cn";

/** Doira shkala — 0 dan 100 gacha.
 *
 * NEGA CHIZIQ EMAS, DOIRA. Ilgari Bozor Salomatligi gorizontal
 * chiziq edi. Chiziq to'g'ri ishlaydi, lekin u sahifaning butun
 * enini egallaydi va yonida boshqa ko'rsatkich turolmaydi. Doira
 * esa ixcham: chap burchakda turadi va o'ng tomonda qator
 * ko'rsatkichga joy qoladi.
 *
 * RANG QIYMATGA QARAB: past — qizil, o'rta — sariq, yuqori —
 * turkuaz. Bular loyihaning o'lchangan ranglari, yangi rang
 * qo'shilmadi.
 *
 * FAQAT RANG EMAS: markazda son ham, ostida so'z bilan tasnif ham
 * turadi. Rang ajrata olmaydigan odam ham holatni biladi.
 */
export function Doira({
  qiymat,
  tasnif,
  sarlavha,
  olcham = 132,
}: {
  /** 0-100. `null` — ma'lumot yo'q. */
  qiymat: number | null;
  tasnif?: string;
  sarlavha: string;
  olcham?: number;
}) {
  const qalinlik = 10;
  const radius = (olcham - qalinlik) / 2;
  const aylana = 2 * Math.PI * radius;
  const toliq = qiymat === null ? 0 : Math.min(100, Math.max(0, qiymat));

  const rang =
    qiymat === null
      ? "var(--rang-matn-past)"
      : toliq >= 60
        ? "var(--rang-yaxshi)"
        : toliq >= 35
          ? "var(--rang-ortacha)"
          : "var(--rang-past-toq)";

  return (
    <div className="flex flex-col items-center">
      <p className="text-matn-past mb-2 text-[11px] tracking-wide uppercase">
        {sarlavha}
      </p>
      <div className="relative" style={{ width: olcham, height: olcham }}>
        <svg
          width={olcham}
          height={olcham}
          // Nol gradusni TEPAGA olib chiqamiz: shkala soat mili
          // yo'nalishida, tepadan boshlanadi — odam shunday kutadi.
          style={{ transform: "rotate(-90deg)" }}
          aria-hidden
        >
          <circle
            cx={olcham / 2}
            cy={olcham / 2}
            r={radius}
            fill="none"
            stroke="var(--rang-panel-yorqin)"
            strokeWidth={qalinlik}
          />
          {qiymat !== null && (
            <circle
              cx={olcham / 2}
              cy={olcham / 2}
              r={radius}
              fill="none"
              stroke={rang}
              strokeWidth={qalinlik}
              strokeLinecap="round"
              strokeDasharray={aylana}
              strokeDashoffset={aylana * (1 - toliq / 100)}
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="raqam text-sarlavha text-2xl leading-none font-bold">
            {qiymat === null ? "—" : qiymat}
          </span>
          {qiymat !== null && (
            <span className="text-matn-past mt-0.5 text-[10px]">/100</span>
          )}
        </div>
      </div>
      {tasnif && (
        <span
          className={cn(
            "mt-2 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
            qiymat === null
              ? "border-matn-past/40 text-matn-past"
              : toliq >= 60
                ? "border-yaxshi/50 text-yaxshi"
                : toliq >= 35
                  ? "border-ortacha/50 text-ortacha"
                  : "border-past/60 text-past",
          )}
        >
          {tasnif}
        </span>
      )}
    </div>
  );
}
