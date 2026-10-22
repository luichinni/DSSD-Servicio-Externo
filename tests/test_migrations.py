from datetime import date

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.cli.seed_certificaciones_demo import cargar_demo
from app.models import Certificacion, ONG, Recurso


def test_migracion_crea_certificaciones_y_revierte_sin_borrar_usuarios(tmp_path, monkeypatch):
    database_url = "sqlite:///" + (tmp_path / "migration.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert {"users", "certificaciones", "ongs", "recursos", "inventario"} <= set(inspect(engine).get_table_names())
    with Session(engine) as db:
        assert cargar_demo(db, date(2026, 10, 17)) == 4
        db.commit()
        assert len(db.scalars(select(Certificacion)).all()) == 4
    command.downgrade(config, "20261015_0001")
    assert "users" in inspect(engine).get_table_names()
    assert "certificaciones" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "certificaciones" in inspect(engine).get_table_names()
    engine.dispose()


def test_migracion_preserva_certificados_previos_y_no_habilita_referencias_desconocidas(tmp_path, monkeypatch):
    database_url = "sqlite:///" + (tmp_path / "legacy.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "20261017_0002")
    engine = create_engine(database_url)
    with engine.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO certificaciones "
            "(id, id_ong, id_recurso, tipo_desastre, rol_permitido, riesgo_maximo, "
            "perfil_competencia, fecha_vencimiento, activa) "
            "VALUES (9, 70, 80, 'hidrologico', 'lote_principal', 'alto', 'Avanzado', '2027-01-01', true)"
        ))
    command.upgrade(config, "head")
    with Session(engine) as db:
        assert db.get(Certificacion, 9).id_ong == 70
        assert db.get(ONG, 70).habilitada is False
        assert db.get(ONG, 70).nombre == "ONG pendiente #70"
        assert db.get(Recurso, 80).nombre == "Recurso pendiente #80"
        assert {fk["referred_table"] for fk in inspect(engine).get_foreign_keys("certificaciones")} == {"ongs", "recursos"}
        # La carga demo no altera las referencias reales pendientes ni su certificado.
        assert cargar_demo(db, date(2026, 10, 20)) == 4
        db.commit()
        assert db.get(ONG, 70).habilitada is False
    command.downgrade(config, "20261017_0002")
    with engine.connect() as conexion:
        assert conexion.scalar(text("SELECT id_ong FROM certificaciones WHERE id = 9")) == 70
    engine.dispose()


def test_demo_completa_solo_sus_placeholders_heredados(tmp_path, monkeypatch):
    database_url = "sqlite:///" + (tmp_path / "demo_legacy.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "20261017_0002")
    engine = create_engine(database_url)
    with engine.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO certificaciones "
            "(id, id_ong, id_recurso, tipo_desastre, rol_permitido, riesgo_maximo, "
            "perfil_competencia, fecha_vencimiento, activa) "
            "VALUES (1, 3, 10, 'inundacion', 'lote_principal', 'alto', 'Avanzado', '2027-01-01', true)"
        ))
    command.upgrade(config, "head")
    with Session(engine) as db:
        assert db.get(ONG, 3).habilitada is False
        assert cargar_demo(db, date(2026, 10, 20)) == 4
        db.commit()
        assert db.get(ONG, 3).habilitada is True
        assert db.get(ONG, 3).nombre == "ONG Demo 3"
        assert db.get(Certificacion, 1).tipo_desastre == "inundacion"
    engine.dispose()
