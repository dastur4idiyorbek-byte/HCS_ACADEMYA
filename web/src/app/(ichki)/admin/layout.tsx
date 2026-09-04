import Link from "next/link";

import { Card } from "@/components/ui/Card";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { kirim } from "@/lib/session";

import { AdminYonMenyu } from "./menyu";

/** Admin bo'limlarining umumiy ramkasi.
 *
 * Adminlik TEKSHIRUVI shu yerda: har bir sahifada takrorlansa, yangi
 * bo'lim qo'shilganda uni unutish oson bo'lardi. Layout esa hech qanday
 * ichki sahifani chetlab o'tib bo'lmaydigan joy.
 *
 * DIQQAT: bu tekshiruv server AMALLARI (server actions) uchun yetarli
 * emas — ular alohida so'rov bo'lib keladi. Shuning uchun `amallar.ts`
 * da ham qayta tekshiriladi.
 */
export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const { admin, til } = await kirim();
  const t = tarjimon(til);

  if (!admin) {
    return (
      <>
        <Sarlavha matn={t("admin.sarlavha")} />
        <Card>
          <p className="text-past text-sm">{t("admin.faqat_admin")}</p>
        </Card>
      </>
    );
  }

  return (
    <>
      <AdminYonMenyu
        bandlar={[
          { yol: "/admin", nom: t("admin.asosiy"), belgi: "💳" },
          { yol: "/admin/signal", nom: t("admin.signal"), belgi: "📈" },
          { yol: "/admin/darslar", nom: t("admin.darslar"), belgi: "🎬" },
          { yol: "/admin/havolalar", nom: t("admin.havolalar"), belgi: "🔗" },
          { yol: "/admin/narxlar", nom: t("admin.narxlar"), belgi: "🏷" },
          { yol: "/admin/halol", nom: t("admin.halol"), belgi: "☪️" },
        ]}
        sarlavha={t("admin.bolimlar")}
      />
      {children}
      <p className="text-matn-past mt-6 text-xs">{t("admin.izoh")}</p>
      <p className="sr-only">
        <Link href="/bosh">{t("menyu.bosh")}</Link>
      </p>
    </>
  );
}
