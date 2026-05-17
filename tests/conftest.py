import os
import tempfile

import pytest

# Use a temp DB for tests
@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    # Patch settings directly
    import weather_bot.config as cfg
    monkeypatch.setattr(cfg.settings, "DB_PATH", db_file)
    return db_file
