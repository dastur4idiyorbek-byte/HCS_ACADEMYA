"use client";

import { useEffect, useRef } from "react";

/** Telegram Login Widget — rasmiy skript.
 *
 * Nima uchun `useRef` va qo'lda qo'shish: widget `<script>` tegining
 * O'ZINI tugmaga aylantiradi (u DOM ga yozadi), ya'ni uni React
 * boshqaradigan oddiy element sifatida qo'yib bo'lmaydi. `next/script`
 * ham mos kelmaydi — u skriptni `<head>` ga ko'chiradi, tugma esa aynan
 * shu joyda paydo bo'lishi kerak.
 *
 * `data-auth-url` — qayta yo'naltirish rejimi: Telegram foydalanuvchini
 * o'sha manzilga query parametrlar bilan qaytaradi. `data-onauth` (JS
 * callback) rejimidan ko'ra sodda va ishonchli: brauzerda JS ishlamay
 * qolsa ham oqim buzilmaydi.
 */
export function TelegramKirish({ botUsername }: { botUsername: string }) {
  const idish = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const joy = idish.current;
    if (!joy || joy.childElementCount > 0) return;

    const skript = document.createElement("script");
    skript.src = "https://telegram.org/js/telegram-widget.js?22";
    skript.async = true;
    skript.setAttribute("data-telegram-login", botUsername);
    skript.setAttribute("data-size", "large");
    skript.setAttribute("data-radius", "12");
    skript.setAttribute("data-userpic", "true");
    skript.setAttribute("data-auth-url", `${window.location.origin}/api/auth/telegram`);
    joy.appendChild(skript);

    return () => {
      joy.replaceChildren();
    };
  }, [botUsername]);

  return <div ref={idish} className="min-h-[48px]" />;
}
