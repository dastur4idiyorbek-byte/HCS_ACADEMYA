"""Settings editor uchun testlar — PF darvozasi va jurnal."""

from __future__ import annotations

from core.admin.settings_editor import MIN_PF, SettingsEditor


def test_pf_past_rad_etiladi(tmp_path) -> None:  # noqa: ANN001
    editor = SettingsEditor(tmp_path / "log.jsonl")
    yozuv = editor.qolla("zanjir.eng_kam_ishonch", 0.0, 0.6, "sinov", backtest_pf=0.5)
    assert not yozuv.qabul_qilindi
    assert f"< {MIN_PF}" in yozuv.rad_sababi


def test_pf_yetarli_qabul(tmp_path) -> None:  # noqa: ANN001
    editor = SettingsEditor(tmp_path / "log.jsonl")
    yozuv = editor.qolla("x", 1, 2, "s", backtest_pf=1.5)
    assert yozuv.qabul_qilindi


def test_rad_ham_jurnalga_yoziladi(tmp_path) -> None:  # noqa: ANN001
    yol = tmp_path / "log.jsonl"
    editor = SettingsEditor(yol)
    editor.qolla("x", 1, 2, "s", backtest_pf=0.5)
    editor.qolla("y", 2, 3, "s", backtest_pf=1.2)

    yozuvlar = editor.oxirgi_yozuvlar()
    assert len(yozuvlar) == 2
    assert yozuvlar[0].qabul_qilindi is False
    assert yozuvlar[1].qabul_qilindi is True


def test_avvalgi_qiymat_saqlanadi(tmp_path) -> None:  # noqa: ANN001
    """Rad etilgan o'zgarish qo'llanmaydi — eski qiymat o'z joyida."""
    editor = SettingsEditor(tmp_path / "log.jsonl")
    eski = 0.0
    yozuv = editor.qolla("k", eski, 0.6, "s", backtest_pf=0.3)
    assert not yozuv.qabul_qilindi
    assert yozuv.eski == eski
