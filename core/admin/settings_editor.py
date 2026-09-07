"""Admin sozlamalar tahriri — chegara o'zgarishlari va jurnal.

QOIDALAR (spec, "Tahririyat — moslashtirish mexanizmi"):
  1. Raqamli chegaralar faqat shu mexanizm orqali o'zgaradi.
  2. Backtest PF < 1.0 bo'lsa o'zgarish RAD ETILADI va avvalgi
     qiymat saqlanadi (hech narsa qo'llanmaydi).
  3. Har bir urinish (qabul ham, rad ham) `settings_log` jurnaliga
     yoziladi.
  4. O'zgarish tizimni AVTOMATIK qayta ishga tushirmaydi — bu sinf
     faqat tekshiradi, yozadi va yangi qiymatni qaytaradi. Qo'llash
     adminning tasdiqlovchi qadamida bo'ladi.

Jurnal formati: JSONL (`settings_log.jsonl`), har qator bitta o'zgarish.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

#: Backtest PF shu qiymatdan past bo'lsa konfiguratsiya rad etiladi.
MIN_PF = 1.0


@dataclass(frozen=True, slots=True)
class SozlamaOzgarishi:
    """Bitta chegara o'zgarishi haqidagi yozuv."""

    kalit: str
    eski: object
    yangi: object
    sabab: str
    pf: float | None
    vaqt: str
    qabul_qilindi: bool
    rad_sababi: str = ""


class SettingsEditor:
    """Chegaralarni tekshiradi, jurnalga yozadi va yangi qiymatni qaytaradi.

    Args:
        jurnal_yoli: `settings_log` fayli yo'li.
    """

    def __init__(self, jurnal_yoli: str | Path = "data/settings_log.jsonl") -> None:
        self._jurnal = Path(jurnal_yoli)

    def tekshir(self, yangi: object, backtest_pf: float | None) -> str:
        """O'zgarishni tekshiradi.

        Returns:
            `"OK"` — qo'llash mumkin, aks holda rad sababi.
        """
        if backtest_pf is not None and backtest_pf < MIN_PF:
            return f"RAD ETILDI: backtest PF {backtest_pf:.2f} < {MIN_PF}"
        return "OK"

    def qolla(
        self,
        kalit: str,
        eski: object,
        yangi: object,
        sabab: str,
        backtest_pf: float | None,
    ) -> SozlamaOzgarishi:
        """Tekshiradi va jurnalga yozadi.

        Rad etilsa ham jurnalga yoziladi (qabul_qilindi=False) — audit
        uchun. Qabul etilgan bo'lsa chaqiruvchi yangi qiymatni
        qo'llaydi; bu sinf fayl/obyektni o'zi O'ZGARTIRMAYDI.
        """
        xato = self.tekshir(yangi, backtest_pf)
        qabul = xato == "OK"
        yozuv = SozlamaOzgarishi(
            kalit=kalit,
            eski=eski,
            yangi=yangi,
            sabab=sabab,
            pf=backtest_pf,
            vaqt=datetime.now(UTC).isoformat(),
            qabul_qilindi=qabul,
            rad_sababi="" if qabul else xato,
        )
        self._jurnal.parent.mkdir(parents=True, exist_ok=True)
        with self._jurnal.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(yozuv), ensure_ascii=False, default=str) + "\n")
        return yozuv

    def oxirgi_yozuvlar(self, soni: int = 20) -> list[SozlamaOzgarishi]:
        """Jurnaldan oxirgi yozuvlarni o'qiydi (monitor uchun)."""
        if not self._jurnal.is_file():
            return []
        natija: list[SozlamaOzgarishi] = []
        with self._jurnal.open("r", encoding="utf-8") as f:
            qatorlar = f.readlines()[-soni:]
        for qator in qatorlar:
            try:
                natija.append(SozlamaOzgarishi(**json.loads(qator)))
            except (json.JSONDecodeError, TypeError):
                continue
        return natija
