import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* `better-sqlite3` — MAHALLIY (native) modul: uning ichida `.node`
     ikkilik fayli bor. Next uni oddiy JS kabi bundlega qo'shishga
     urinsa, ikkilik fayl yo'li buziladi va modul ishga tushish paytida
     yiqiladi — ba'zan toza xato bilan emas, butun JARAYONNI o'ldirib.
     Serverda bu 502 bo'lib ko'rinadi (500 emas!), ya'ni ilova xato
     qaytarmaydi, umuman javob bermaydi.

     `serverExternalPackages` Next'ga aytadi: bu paketni qo'llama, uni
     ishga tushirish paytida `node_modules` dan o'qi.

     Mahalliy ishlab chiqishda bu muammo ko'rinmaydi, chunki fayllar
     baribir o'z joyida turadi. */
  serverExternalPackages: ["better-sqlite3"],
};

export default nextConfig;
