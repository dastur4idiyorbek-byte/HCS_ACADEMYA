/** Signal kirish nuqtasidan narx qancha uzoqlashgani.
 *
 * SOF FUNKSIYA va shuning uchun ALOHIDA FAYLDA: uni brauzerdagi
 * komponent ham ishlatadi. Binance'dan narx olish esa `jonli-server.ts`
 * da — u `node:fs` ni tortadi va klient to'plamiga tushmasligi kerak.
 */
export function ozgarishFoizi(kirish: number, hozir: number): number | null {
  if (!Number.isFinite(kirish) || !Number.isFinite(hozir) || kirish <= 0)
    return null;
  return ((hozir - kirish) / kirish) * 100;
}
