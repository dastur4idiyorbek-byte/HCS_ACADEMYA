"""Video jildi qoidasi — bot va sayt BIR XIL joyni ko'rsatishi shart.

Sayt faylni yozadi, bot esa uni Telegramga chiqaradi. Ikkalasi jildni
o'zi hisoblaydi (biri Pythonda, biri TypeScriptda) — qoida ayrilib
ketsa, sayt yozgan faylni bot topa olmaydi va dars botda jimgina
ko'rinmay qoladi.

Saytdagi nusxasi: `web/src/lib/media.ts` -> `videoJildi()`,
`web/tests/media.test.ts` da shu qiymatlar tekshiriladi.
"""

from pathlib import Path

from bot.hosting import signal_media_dir, sqlite_file, video_dir


def test_uch_qiyshiq_chiziq_nisbiy_yol() -> None:
    assert sqlite_file("sqlite+aiosqlite:///data/hcs.db") == Path("data/hcs.db")


def test_tort_qiyshiq_chiziq_mutlaq_yol() -> None:
    assert sqlite_file("sqlite+aiosqlite:////data/hcs.db") == Path("/data/hcs.db")


def test_sqlite_bolmagan_manzil_none() -> None:
    assert sqlite_file("postgresql://localhost/hcs") is None


def test_video_jildi_baza_yonida() -> None:
    # Saytdagi test ayni shu qiymatni kutadi.
    assert video_dir("sqlite+aiosqlite:////data/hcs.db") == Path("/data/video")


def test_manzil_yoq_bolsa_data_jildi() -> None:
    assert video_dir("").name == "video"
    assert video_dir("").parent.name == "data"


# --------------------------------------------------------------------- #
#  Signal grafiklari jildi (4-prompt, 4-qism)
# --------------------------------------------------------------------- #


def test_signal_media_jildi_baza_yonida() -> None:
    """Sayt rasmni yozadi, bot uni Telegramga chiqaradi.

    Ikkalasi jildni o'zi hisoblaydi (biri Pythonda, biri
    TypeScriptda). Qoida ayrilib ketsa, admin yuklagan grafik botda
    JIMGINA ko'rinmay qolardi — hech qanday xato xabarisiz.

    Saytdagi nusxasi: `web/src/lib/media.ts` -> `signalJildi()`.
    """
    assert signal_media_dir("sqlite+aiosqlite:////data/hcs.db") == Path("/data/signal-media")


def test_signal_media_video_bilan_ARALASHMAYDI() -> None:
    """Ikkisi alohida jild.

    Bir jildda tursa, post yoki video o'chirilganda bir xil nomli
    signal rasmini tasodifan o'chirib yuborish mumkin bo'lardi.
    """
    manzil = "sqlite+aiosqlite:////data/hcs.db"
    assert signal_media_dir(manzil) != video_dir(manzil)
