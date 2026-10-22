import pytest

from app.core.config import get_database_url


@pytest.mark.parametrize("prefix", ["postgresql://", "postgres://", "postgresql+psycopg://"])
def test_url_postgresql_usa_el_driver_instalado(monkeypatch, prefix):
    monkeypatch.setenv("DATABASE_URL", prefix + "user:password@localhost/db")
    assert get_database_url() == "postgresql+psycopg://user:password@localhost/db"
