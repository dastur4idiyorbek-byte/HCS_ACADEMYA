import { readFile } from "node:fs/promises";
import path from "node:path";

/** Kitob mazmuni — SERVER TOMONDA o'qiladi.
 *
 * NEGA `import` EMAS. JSON ni to'g'ridan-to'g'ri import qilsak, u
 * sayt to'plamiga (bundle) kirib ketardi — 339 KB ortiqcha yuk.
 * Bu yerda esa u so'rov paytida diskdan o'qiladi va faqat
 * chizilgan HTML brauzerga boradi.
 *
 * MANBA BITTA. Bu fayl `python -m scripts.kitob.eksport` tomonidan
 * yasaladi va u PDF bilan AYNAN BIR XIL funksiyalardan o'qiydi.
 * Ya'ni saytdagi matn PDF dan ajralib keta olmaydi.
 */

export type Blok =
  | { tur: "matn" | "h2" | "h3" | "izoh" | "savol" | "chizma_izoh"; matn: string }
  | { tur: "royxat"; matn: string }
  | { tur: "chizma"; svg: string }
  | { tur: "xulosa" | "savollar" | "real_misol"; qatorlar: string[] }
  | { tur: "jadval"; sarlavha: string[]; qatorlar: string[][] };

export type Bob = { raqam: string; nom: string; bloklar: Blok[] };
export type KitobBolimi = { kalit: string; boblar: Bob[] };

let kesh: KitobBolimi[] | null = null;

/** Barcha bo'limlar. Birinchi o'qishdan keyin xotirada qoladi. */
export async function kitobMazmuni(): Promise<KitobBolimi[]> {
  if (kesh !== null) return kesh;
  try {
    const xom = await readFile(
      path.join(process.cwd(), "kitob", "mazmun.json"),
      "utf8",
    );
    kesh = (JSON.parse(xom) as { bolimlar: KitobBolimi[] }).bolimlar;
  } catch {
    // Eksport yugurtirilmagan — sahifa "hali tayyor emas" deydi,
    // sayt esa yiqilmaydi.
    kesh = [];
  }
  return kesh;
}

export async function kitobBolimi(kalit: string): Promise<KitobBolimi | null> {
  const hammasi = await kitobMazmuni();
  return hammasi.find((b) => b.kalit === kalit) ?? null;
}
