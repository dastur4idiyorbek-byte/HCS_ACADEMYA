import { redirect } from "next/navigation";

/** Eski manzil — mazmuni Bozor Salomatligi sahifasiga ko'chdi.
 *
 * Sahifa o'chirilmadi, yo'naltiriladi: eski havola yoki xatcho'p
 * "404" bermasin. Menyuda bu band endi yo'q. */
export default function EskiSokinlik() {
  redirect("/salomatlik");
}
