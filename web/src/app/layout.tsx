import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

/* Kirill alifbosi ATAYLAB qo'shilgan: sayt o'zbek va rus tillarida
   ishlaydi (8-bo'lim). Shrift kirillni qo'llab-quvvatlamasa, rus tilidagi
   matn brauzerning zaxira shriftiga tushib, sahifa ikki xil ko'rinadi. */
const inter = Inter({
  subsets: ["latin", "latin-ext", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Halol Crypto Savdo",
  description:
    "Halol kripto spot savdo signallari — bozor salomatligi, statistika va portfel.",
  icons: { icon: "/logo-180.png", apple: "/logo-180.png" },
};

export const viewport: Viewport = {
  themeColor: "#0a2450",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="uz" className={inter.variable}>
      <body className="min-h-dvh font-sans antialiased">{children}</body>
    </html>
  );
}
