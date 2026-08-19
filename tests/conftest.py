"""Umumiy test fixtures."""

from __future__ import annotations

import pytest

from core.config import load_config
from core.config.schema import AppConfig


@pytest.fixture(scope="session")
def config() -> AppConfig:
    """Haqiqiy `config/default.yaml` — sozlamalar bilan kod mos kelishini ham sinaydi."""
    return load_config("config/default.yaml")
