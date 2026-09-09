/** Ticker → CoinGecko `id` jadvali.
 *
 * NEGA BU JADVAL KERAK. Biz coinlarni ticker bilan bilamiz (`BTC`),
 * CoinGecko esa o'z `id` si bilan so'raydi (`bitcoin`). Ikkisi
 * orasida formula yo'q — faqat ro'yxat.
 *
 * NEGA BU XAVFLI. Bitta ticker bir necha coinga tegishli bo'lishi
 * mumkin. `id` ni bir harf xato yozsak, saytda BOSHQA COINNING
 * narxi chiqadi va buni hech kim sezmaydi: raqam bor, grafik bor,
 * hammasi ishlayotgandek ko'rinadi.
 *
 * CrypoIslam kanalining har bir kartasida ham aynan shu ogohlantirish
 * turadi: "coinga kirishdan oldin ikonka va logotipni tekshiring,
 * ba'zi coinlarning nomi bir xil".
 *
 * NIMA UCHUN JADVALGA ISHONILMAYDI. Bu jadval qo'lda yozilgan va
 * CoinGecko'da bittalab tekshirilmagan. Shuning uchun u YAGONA
 * himoya emas: `bozor-server.ts` javobdagi `symbol` maydonini biz
 * kutgan ticker bilan solishtiradi va mos kelmasa qatorni TASHLAB
 * YUBORADI. Ya'ni xato jadval "boshqa coin narxi" emas, "ma'lumot
 * yo'q" bo'lib chiqadi — jimgina aldash o'rniga ochiq bo'shliq.
 *
 * `web/tests/coingecko-id.test.ts` jadval 80 talik ro'yxatni to'liq
 * qamrashini tekshiradi.
 */
export const COINGECKO_ID: Record<string, string> = {
  BTC: "bitcoin",
  ETH: "ethereum",
  SOL: "solana",
  ADA: "cardano",
  AVAX: "avalanche-2",
  LINK: "chainlink",
  DOT: "polkadot",
  BCH: "bitcoin-cash",
  LTC: "litecoin",
  NEAR: "near",
  ETC: "ethereum-classic",
  FIL: "filecoin",
  APT: "aptos",
  SUI: "sui",
  POL: "polygon-ecosystem-token",
  XLM: "stellar",
  HBAR: "hedera-hashgraph",
  VET: "vechain",
  ATOM: "cosmos",
  OP: "optimism",
  ARB: "arbitrum",
  TAO: "bittensor",
  TIA: "celestia",
  STX: "blockstack",
  IMX: "immutable-x",
  GRT: "the-graph",
  RENDER: "render-token",
  ALGO: "algorand",
  EGLD: "elrond-erd-2",
  THETA: "theta-token",
  S: "sonic-3",
  PYTH: "pyth-network",
  FLOW: "flow",
  MINA: "mina-protocol",
  AR: "arweave",
  CKB: "nervos-network",
  ZIL: "zilliqa",
  ONE: "harmony",
  KSM: "kusama",
  CELO: "celo",
  BAT: "basic-attention-token",
  IOTA: "iota",
  XTZ: "tezos",
  QTUM: "qtum",
  NEO: "neo",
  STORJ: "storj",
  SC: "siacoin",
  RVN: "ravencoin",
  MASK: "mask-network",
  API3: "api3",
  TRB: "tellor",
  ICX: "icon",
  ONT: "ontology",
  ASTR: "astar",
  MOVR: "moonriver",
  STRAX: "stratis",
  PHA: "pha",
  REQ: "request-network",
  BICO: "biconomy",
  RARE: "superrare",
  JASMY: "jasmycoin",
  STRK: "starknet",
  XEC: "ecash",
  TFUEL: "theta-fuel",
  HOT: "holotoken",
  IOST: "iostoken",
  STEEM: "steem",
  HIVE: "hive",
  ACH: "alchemy-pay",
  RIF: "rif-token",
  CTSI: "cartesi",
  EDU: "edu-coin",
  DYM: "dymension",
  SAGA: "saga-2",
  TWT: "trust-wallet-token",
  CHR: "chromaway",
  AVA: "concierge-io",
  CVC: "civic",
  QKC: "quark-chain",
  DGB: "digibyte",
};

/** `id` si CoinGecko'da TEKSHIRILMAGAN tickerlar.
 *
 * Bular xotiradan yozilgan va noaniq: coin nomini o'zgartirgan
 * (STRAX → Xertra), yangi (S, SAGA, EDU), yoki ticker boshqa
 * loyihalarda ham uchraydi (AVA, PHA, RIF, ONE, HOT).
 *
 * Ro'yxat ayblov emas, ESLATMA: kimdir CoinGecko'ni ochib bittalab
 * tekshirsa, avval shularni tekshirsin. Tekshirilgani shu yerdan
 * o'chiriladi.
 *
 * Kod bu ro'yxatga QARAB ish tutmaydi — himoya `symbol` tekshiruvida,
 * bu yerda emas. Ya'ni ro'yxat eskirsa ham xavf tug'ilmaydi.
 */
export const TEKSHIRILMAGAN: ReadonlySet<string> = new Set([
  "S",
  "STRAX",
  "PHA",
  "RIF",
  "EDU",
  "SAGA",
  "AVA",
  "CHR",
  "ONE",
  "HOT",
  "RARE",
]);
