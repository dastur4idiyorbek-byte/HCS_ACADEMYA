/** Telegram Bot API — faqat xabar yuborish uchun.
 *
 * Nima uchun kerak: admin to'lovni BOTDA tasdiqlaganda foydalanuvchiga
 * "obunangiz ochildi" degan xabar boradi. Sayt orqali tasdiqlansa ham
 * o'sha xabar borishi SHART — aks holda foydalanuvchi uchun natija
 * qaysi vositadan tasdiqlanganiga qarab har xil bo'ladi, ya'ni sayt
 * botning o'rnini bosolmaydi.
 */

export async function xabarYubor(
  botToken: string,
  chatId: number,
  matn: string,
): Promise<boolean> {
  try {
    const javob = await fetch(
      `https://api.telegram.org/bot${botToken}/sendMessage`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          text: matn,
          parse_mode: "HTML",
        }),
        // Telegram javob bermay qolsa, admin paneli muzlab qolmasin
        signal: AbortSignal.timeout(8000),
      },
    );
    return javob.ok;
  } catch {
    // Xabar bormasa ham to'lov TASDIQLANGAN bo'lib qoladi — bu to'g'ri
    // tartib: bazadagi holat asosiy, xabar esa qo'shimcha.
    return false;
  }
}
