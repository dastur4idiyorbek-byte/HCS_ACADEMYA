import { JonliOshxona } from "@/components/JonliOshxona";
import { Sarlavha } from "@/components/ui/Sarlavha";
import { tarjimon } from "@/lib/i18n";
import { jonliHolat } from "@/lib/queries";
import { kirim } from "@/lib/session";

/** Har so'rovda yangi ma'lumot — bu monitorning butun ma'nosi. */
export const dynamic = "force-dynamic";

/** 👨‍🍳 Jonli Oshxona — tizim orqa fonda nima qilayotgani.
 *
 * ADMINLIK TEKSHIRUVI `admin/layout.tsx` DA: sahifa shu ramka ichida
 * turgani uchun uni chetlab o'tib bo'lmaydi. Sahifa har necha soniyada
 * o'qiydigan `/api/jonli` esa ALOHIDA so'rov — u yerda tekshiruv
 * qaytadan qilinadi (server amallaridagi kabi).
 *
 * NIMA UCHUN FAQAT SAYTDA: botda bunday tezlikdagi yangilanish
 * o'nlab Telegram xabariga aylanardi. Shuning uchun bu funksiya
 * botga qo'shilmaydi.
 */
export default async function JonliSahifa() {
  const { til } = await kirim();
  const t = tarjimon(til);
  const holat = jonliHolat();

  const matnlar = {
    sarlavha: t("oshxona.sarlavha"),
    izoh: t("oshxona.izoh"),
    kirish: t("oshxona.kirish"),
    yoq: t("oshxona.yoq"),
    coin_yoq: t("oshxona.coin_yoq"),
    oxirgi_sikl: t("oshxona.oxirgi_sikl"),
    uzildi: t("oshxona.uzildi"),
    sikl_toxtadi: t("oshxona.sikl_toxtadi"),
    signal_chiqdi: t("oshxona.signal_chiqdi"),
    ball: t("oshxona.ball"),
    jami: t("oshxona.jami"),
    signal_soni: t("oshxona.signal_soni"),
    eng_kop: t("oshxona.eng_kop"),
    ortacha_ball: t("oshxona.ortacha_ball"),
    eng_yuqori: t("oshxona.eng_yuqori"),
  };

  // Bosqich nomlari BIR MARTA, to'liq ro'yxat bilan uzatiladi — polling
  // paytida kelgan yangi bosqich ham nomi bilan chiqsin.
  //
  // Kalitlar qo'lda yozilgan (`t("oshxona.b_...")`), chunki
  // `tests/i18n.test.ts` aynan shunday yozilgan kalitlarni tekshiradi:
  // shablon satri (`t(\`oshxona.b_${x}\`)`) bo'lsa, yetishmayotgan
  // tarjima jimgina ekranga chiqib ketardi.
  const bosqichNomlari: Record<string, string> = {
    halal: t("oshxona.b_halal"),
    data: t("oshxona.b_data"),
    zones: t("oshxona.b_zones"),
    zone_position: t("oshxona.b_zone_position"),
    timeframes: t("oshxona.b_timeframes"),
    indicators: t("oshxona.b_indicators"),
    confirmation: t("oshxona.b_confirmation"),
    levels: t("oshxona.b_levels"),
    structure: t("oshxona.b_structure"),
    session: t("oshxona.b_session"),
    window: t("oshxona.b_window"),
    range: t("oshxona.b_range"),
    volume: t("oshxona.b_volume"),
    breakout: t("oshxona.b_breakout"),
    threshold: t("oshxona.b_threshold"),
    risk_engine: t("oshxona.b_risk_engine"),
    market_health: t("oshxona.b_market_health"),
    no_setup: t("oshxona.b_no_setup"),
    error: t("oshxona.b_error"),
  };

  return (
    <>
      <Sarlavha matn={`👨‍🍳 ${matnlar.sarlavha}`} />
      <JonliOshxona
        boshlangich={holat}
        matnlar={matnlar}
        bosqichNomlari={bosqichNomlari}
      />
    </>
  );
}
