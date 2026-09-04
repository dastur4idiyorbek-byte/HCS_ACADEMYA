/** Bozor Salomatligi sahifasidagi terminal toifalari (4-prompt, 2-qism).
 *
 * FAQAT HALOL SKRININGDAN O'TGAN COINLAR. Ro'yxat zanjir moduli
 * kuzatadigan o'n ikki coin bilan AYNAN bir xil: o'z saytimizda
 * haram yoki shubhali coinning grafigini ko'rsatish — mahsulotning
 * o'z va'dasiga zid bo'lardi.
 *
 * Toifalar QO'LDA yozilgan va bu ataylab: coin qaysi sektorga
 * tegishli ekani bozor ma'lumoti emas, TASNIF. Uni avtomatik
 * "aniqlash" — o'ylab topilgan raqam bo'lardi.
 */

export type Terminal = {
  /** Coin belgisi (`BTC`) */
  symbol: string;
  /** TradingView juftligi (`BINANCE:BTCUSDT`) */
  tradingview: string;
  izoh: string;
};

export type Toifa = {
  kod: string;
  /** i18n kaliti */
  kalit: string;
  guruhlar: { nom: string; coinlar: string[] }[];
};

/** Zanjir moduli kuzatadigan coinlar — `config/default.yaml` dagi
 *  `zanjir.kuzatiladigan_coinlar` bilan bir xil bo'lishi shart.
 *  `web/tests/terminal.test.ts` buni tekshiradi. */
export const TERMINAL_COINLARI = [
  "BTC",
  "ETH",
  "SOL",
  "ADA",
  "AVAX",
  "LINK",
  "DOT",
  "ATOM",
  "LTC",
  "NEAR",
  "ETC",
  "FIL",
] as const;

export const TOIFALAR: Toifa[] = [
  {
    kod: "sektorlar",
    kalit: "zanjir.tab_sektorlar",
    guruhlar: [
      {
        nom: "Smart-kontrakt platformalari",
        coinlar: ["ETH", "SOL", "ADA", "AVAX", "NEAR", "ETC"],
      },
      { nom: "Qiymat saqlash va to'lov", coinlar: ["BTC", "LTC"] },
      { nom: "Infratuzilma (oracle, saqlash)", coinlar: ["LINK", "FIL"] },
      { nom: "O'zaro bog'lanish", coinlar: ["DOT", "ATOM"] },
    ],
  },
  {
    kod: "ekotizim",
    kalit: "zanjir.tab_ekotizim",
    guruhlar: [
      { nom: "Bitcoin", coinlar: ["BTC", "LTC"] },
      { nom: "Ethereum", coinlar: ["ETH", "ETC"] },
      { nom: "Solana", coinlar: ["SOL"] },
      { nom: "Cosmos", coinlar: ["ATOM"] },
      { nom: "Polkadot", coinlar: ["DOT", "AVAX"] },
      { nom: "Boshqalar", coinlar: ["ADA", "NEAR", "LINK", "FIL"] },
    ],
  },
];

/** Coindan TradingView juftligini yasaydi. */
export function tradingviewJuftligi(
  symbol: string,
  kotirovka = "USDT",
): string {
  return `BINANCE:${symbol.toUpperCase()}${kotirovka}`;
}

/** Coindan Binance juftligini yasaydi (narx so'rovi uchun). */
export function binanceJuftligi(symbol: string, kotirovka = "USDT"): string {
  return `${symbol.toUpperCase()}${kotirovka}`;
}
