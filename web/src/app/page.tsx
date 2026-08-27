import { redirect } from "next/navigation";

import { kirim } from "@/lib/session";

/** Ildiz sahifa — kirgan bo'lsa Bosh sahifaga, aks holda kirishga. */
export default async function Ildiz() {
  const { kirgan } = await kirim();
  redirect(kirgan ? "/bosh" : "/kirish");
}
