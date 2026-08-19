"""Logging tizimi (6.4-band).

Ayniqsa quyidagilar log qilinishi SHART:
  - WebSocket uzilishi va qayta ulanish
  - Risk Engine tomonidan signal to'xtatilishi (qaysi qoida sababli)
  - Kill switch ishga tushishi
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-38s | %(message)s"


def setup_logging(
    level: str = "INFO",
    log_dir: str | Path | None = "logs",
    rotate_mb: int = 20,
    backups: int = 5,
) -> None:
    """Ildiz loggerni bir marta sozlaydi (konsol + aylanuvchi fayl)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_dir is not None:
        directory = Path(log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            directory / "hcs.log",
            maxBytes=rotate_mb * 1024 * 1024,
            backupCount=backups,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Modul uchun logger qaytaradi."""
    return logging.getLogger(name)
