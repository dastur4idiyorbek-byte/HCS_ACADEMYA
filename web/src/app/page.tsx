import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHint, CardTitle } from "@/components/ui/Card";
import { Logo } from "@/components/ui/Logo";

/* 1-BOSQICH: dizayn tizimini KO'Z BILAN tekshirish sahifasi.
   3-bosqichda haqiqiy Bosh sahifa bilan almashtiriladi. */

const RANGLAR = [
  { nom: "H turkuaz", hex: "#01AAC1", joy: "(210, 300)", rol: "matn manbai" },
  { nom: "H turkuaz och", hex: "#00BCD5", joy: "(270, 318)", rol: "sarlavha" },
  { nom: "C apelsin", hex: "#F47F16", joy: "(420, 185)", rol: "ramka" },
  { nom: "S ko'k", hex: "#10469C", joy: "(440, 370)", rol: "ko'tarilgan fon" },
  { nom: "S ko'k to'q", hex: "#133C7C", joy: "(55, 590)", rol: "kartochka foni" },
  { nom: "Sariq", hex: "#F0B02A", joy: "(600, 25)", rol: "o'rtacha holat" },
  { nom: "Oq", hex: "#F9F9F9", joy: "(560, 120)", rol: "logotip foni" },
];

export default function DizaynTizimi() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <Logo size={44} />
        <Badge tone="ortacha">1-bosqich · dizayn tizimi</Badge>
      </header>

      <div className="space-y-5">
        <Card variant="urgu">
          <CardTitle>Ranglar logotipdan o&apos;qildi</CardTitle>
          <CardHint>
            Har bir qiymat <code className="text-sarlavha">public/logo.jpg</code> faylidan
            aniq koordinata bo&apos;yicha o&apos;lchangan (9×9 mediana), taxmin
            qilinmagan. Qayta tekshirish:{" "}
            <code className="text-sarlavha">python3 scripts/logo_ranglari.py</code>
          </CardHint>

          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {RANGLAR.map((r) => (
              <li
                key={r.hex}
                className="border-ramka-yumshoq rounded-kichik flex items-center gap-3 border p-2.5"
              >
                <span
                  aria-hidden
                  className="rounded-kichik h-9 w-9 shrink-0 border border-white/15"
                  style={{ background: r.hex }}
                />
                <span className="min-w-0">
                  <span className="text-sarlavha block text-sm font-medium">{r.nom}</span>
                  <span className="text-matn-past raqam block text-xs">
                    {r.hex} · {r.joy} · {r.rol}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <div className="grid gap-5 sm:grid-cols-2">
          <Card>
            <CardTitle>Tugmalar</CardTitle>
            <CardHint>Asosiy amal apelsin, ikkilamchisi faqat ramka bilan.</CardHint>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button>To&apos;lov qilish</Button>
              <Button variant="ikkilamchi">Batafsil</Button>
              <Button variant="shaffof">Bekor qilish</Button>
            </div>
            <div className="mt-3">
              <Button disabled>Tez kunda</Button>
            </div>
          </Card>

          <Card>
            <CardTitle>Holat yorliqlari</CardTitle>
            <CardHint>Signal holati, bozor salomatligi, obuna tarifi uchun.</CardHint>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone="yaxshi">🟢 Yaxshi</Badge>
              <Badge tone="ortacha">🟡 O&apos;rtacha</Badge>
              <Badge tone="past">🔴 Past</Badge>
              <Badge>Tez kunda</Badge>
            </div>
          </Card>
        </div>

        <Card>
          <CardTitle>Matn ierarxiyasi</CardTitle>
          <p className="mt-3 text-sm leading-relaxed">
            Asosiy matn logotip ko&apos;kining och tonida — turkuaz uzun matnda
            ko&apos;zni charchatadi, shuning uchun u sarlavha va urg&apos;u uchun
            saqlanadi. Kontrast: sarlavha 4.66:1, asosiy matn 7.14:1 — ikkalasi ham
            WCAG AA talabidan yuqori. Har bir juftlikni{" "}
            <code className="text-sarlavha">python3 scripts/kontrast.py</code>{" "}
            CSS faylining o&apos;zidan o&apos;qib tekshiradi.
          </p>
          <p className="text-matn-past mt-2 text-sm">
            Ikkinchi darajali matn — izoh, sana, manba ko&apos;rsatkichlari uchun.
          </p>
        </Card>
      </div>
    </main>
  );
}
