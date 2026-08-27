/** Suv belgisini takrorlanuvchi fon rasmi sifatida quradi.
 *
 * Nima uchun CSS `content` emas: matn butun kartochka bo'ylab
 * TAKRORLANISHI kerak. `content` bitta qator beradi va uni skrinshotdan
 * qirqib tashlash oson. SVG esa kafel bo'lib yotadi — kadrning qaysi
 * qismini kessangiz ham, ID ichida qoladi.
 *
 * Nima uchun alohida fayl: `Himoya.tsx` — brauzer komponenti ("use
 * client"), uni testda import qilib bo'lmaydi. Bu yerdagi funksiya esa
 * sof — kirish matni beriladi, CSS chiqadi.
 */

/** Kafel o'lchami matn burchagiga MOSLANGAN. Kattaroq bo'lsa, kichik
 *  kartochkaga bitta qator ham sig'may qoladi va suv belgisi umuman
 *  ko'rinmaydi — dastlab aynan shunday bo'lgan edi. */
const KENGLIK = 170;
const BALANDLIK = 78;

export function suvBelgisiUslubi(matn: string): {
  backgroundImage: string;
  backgroundRepeat: "repeat";
} {
  // SVG — XML: `<`, `>`, `&`, tirnoqlar strukturani buzadi. Belgi bazadan
  // keladi, ya'ni ishonchli emas deb qaraymiz.
  const xavfsiz = matn.replace(/[<>&"']/g, "").slice(0, 64);
  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' width='${KENGLIK}' height='${BALANDLIK}'>` +
    `<text x='6' y='50' transform='rotate(-20 85 39)' font-family='sans-serif' ` +
    `font-size='11' font-weight='700' fill='%23ffffff' fill-opacity='0.17'>${xavfsiz}</text>` +
    `</svg>`;
  return {
    backgroundImage: `url("data:image/svg+xml,${encodeURIComponent(svg).replace(/'/g, "%27")}")`,
    backgroundRepeat: "repeat",
  };
}
