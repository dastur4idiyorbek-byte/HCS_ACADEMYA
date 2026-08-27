import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Bo'sh: mahalliy (native) modul yo'q, shuning uchun
     `serverExternalPackages` ham kerak emas. Baza `node:sqlite` orqali
     o'qiladi — u Node'ning o'ziga kirgan, ikkilik fayli yo'q. */
};

export default nextConfig;
