import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Mahalliy (native) modul yo'q, shuning uchun `serverExternalPackages`
     kerak emas. Baza `node:sqlite` orqali o'qiladi — u Node'ning o'ziga
     kirgan, ikkilik fayli yo'q. */

  images: {
    /* Coin logotiplari CoinGecko'ning suratlar tarmog'idan keladi.
       Next.js tashqi manbani ATAYLAB ro'yxatsiz yuklamaydi: aks holda
       istalgan manzil sayt nomidan rasm uzatishi mumkin bo'lardi.
       Shuning uchun faqat shu ikki uy nomi ochiladi — eskisi hali ham
       ba'zi coinlarda uchraydi. */
    remotePatterns: [
      { protocol: "https", hostname: "coin-images.coingecko.com" },
      { protocol: "https", hostname: "assets.coingecko.com" },
    ],
  },
};

export default nextConfig;
