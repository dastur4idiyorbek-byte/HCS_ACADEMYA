/** Ko'rsatiladigan sektorlar — QO'LDA tanlangan ro'yxat.
 *
 * NEGA QO'LDA TANLANADI, HAMMASI EMAS. CoinGecko ikki yuzdan
 * ortiq "toifa" beradi va ularning ko'pi sektor emas:
 *
 *     "Made in USA", "Made in China"      — geografiya, sektor emas
 *     "CoinList Launchpad"                — qayerda sotilgani
 *     "GENIUS Act Compliant Stablecoin"   — huquqiy holat
 *     "Alleged SEC Securities"            — sud ishi
 *     "Proof of Work" / "Proof of Stake"  — texnologiya, tarmoq emas
 *
 * Bularni ko'rsatish foydalanuvchini chalg'itadi: u "sektor" degan
 * so'zni ko'rib, biznes yo'nalishini kutadi.
 *
 * IKKINCHI, MUHIMROQ SABAB: toifalar USTMA-UST TUSHADI. Bitta coin
 * o'nlab toifada bo'lishi mumkin. "Smart Contract Platform" va
 * "Layer 1" deyarli bir xil coinlar — ularning kapitali qo'shilsa,
 * butun bozordan katta son chiqadi. Shuning uchun bu ro'yxatda
 * bir-birini deyarli takrorlaydigan toifalardan FAQAT BITTASI
 * qoldirilgan.
 *
 * Ro'yxat `lib/terminallar.ts` dagi TOIFALAR bilan bir mantiqda:
 * tasniflash — bozor ma'lumoti emas, QAROR. Uni avtomatlashtirish
 * xatolarni ko'rinmas qiladi.
 */
export const KORSATILADIGAN_SEKTORLAR: { id: string; nom: string }[] = [
  { id: "layer-1", nom: "Layer 1" },
  { id: "layer-2", nom: "Layer 2" },
  { id: "decentralized-finance-defi", nom: "DeFi" },
  { id: "artificial-intelligence", nom: "AI" },
  { id: "gaming", nom: "Gaming" },
  { id: "real-world-assets-rwa", nom: "RWA" },
  { id: "depin", nom: "DePIN" },
  { id: "oracle", nom: "Oracle" },
  { id: "storage", nom: "Saqlash" },
  { id: "privacy-coins", nom: "Maxfiylik" },
  { id: "interoperability", nom: "O'zaro bog'lanish" },
  { id: "metaverse", nom: "Metaverse" },
  { id: "non-fungible-tokens-nft", nom: "NFT" },
  { id: "identity", nom: "Identifikatsiya" },
  { id: "infrastructure", nom: "Infratuzilma" },
];

/** Faqat tanlangan sektorlarni qoldiradi va nomini bizniki bilan
 *  almashtiradi. Tartib — shu ro'yxatdagi tartib, kapital bo'yicha
 *  emas: kapital ustma-ust hisoblangani uchun u bo'yicha saralash
 *  ham chalg'itardi. */
export function sektorlarniSaralash<T extends { id: string; nom: string }>(
  hammasi: T[],
): T[] {
  const boyicha = new Map(hammasi.map((s) => [s.id, s]));
  const natija: T[] = [];
  for (const kerakli of KORSATILADIGAN_SEKTORLAR) {
    const topilgan = boyicha.get(kerakli.id);
    if (topilgan) natija.push({ ...topilgan, nom: kerakli.nom });
  }
  return natija;
}
