from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.compromiso_recurso import CompromisoRecurso, EstadoCompromiso
from app.models.inventario import Inventario
from app.models.user import User


@pytest.fixture
def test_env(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, sessionmaker[Session], str], None, None]:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-key-that-is-at-least-32-bytes-long")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )

    def override_get_db() -> Generator[Session, None, None]:
        with test_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    with test_session_factory() as db:
        user = User(email="coordinador@emergencias.gob.ar", hashed_password=hash_password("clave123"))
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    with TestClient(app) as client:
        yield client, test_session_factory, token

    app.dependency_overrides.clear()
    engine.dispose()


def test_liberar_requiere_autenticacion(test_env):
    client, _, _ = test_env
    res = client.post(
        "/api/v1/proyectos/liberar-recursos",
        json={"id_emergencia": 101, "id_ong": 3, "motivo_cierre": "cierre", "recursos_a_liberar": [{"id_recurso": 10, "cantidad_liberada": 1}]},
    )
    assert res.status_code == 401


def test_liberar_exitoso_todos_los_recursos_de_la_ong(test_env):
    client, session_factory, token = test_env
    ahora = datetime.now(timezone.utc)
    with session_factory() as db:
        # Inventario de ONG 3 con stock descontado
        db.add(Inventario(ong_id=3, recurso_id=10, cantidad_total=100, cantidad_disponible=50))
        db.add(Inventario(ong_id=3, recurso_id=12, cantidad_total=30, cantidad_disponible=10))

        # Compromisos activos de ONG 3 en emergencia 101
        db.add(
            CompromisoRecurso(
                id_emergencia=101,
                id_oferta=15,
                id_ong=3,
                id_recurso=10,
                cantidad_comprometida=50,
                estado=EstadoCompromiso.COMPROMETIDO,
                fecha_bloqueo=ahora,
            )
        )
        db.add(
            CompromisoRecurso(
                id_emergencia=101,
                id_oferta=16,
                id_ong=3,
                id_recurso=12,
                cantidad_comprometida=20,
                estado=EstadoCompromiso.COMPROMETIDO,
                fecha_bloqueo=ahora,
            )
        )

        # Compromiso de OTRA ONG (no debe liberarse)
        db.add(
            CompromisoRecurso(
                id_emergencia=101,
                id_oferta=20,
                id_ong=9,
                id_recurso=10,
                cantidad_comprometida=15,
                estado=EstadoCompromiso.COMPROMETIDO,
                fecha_bloqueo=ahora,
            )
        )
        db.commit()

    payload = {
        "id_emergencia": 101,
        "id_ong": 3,
        "motivo_cierre": "finalizacion_tareas",
        "recursos_a_liberar": [{"id_recurso": 10, "cantidad_liberada": 50}],
    }

    res = client.post(
        "/api/v1/proyectos/liberar-recursos",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["estado"] == "liberacion_exitosa"
    assert data["id_ong"] == 3
    assert data["total_recursos_liberados"] == 70  # 50 + 20

    with session_factory() as db:
        # Stock disponible restaurado para ONG 3
        inv10 = db.query(Inventario).filter_by(ong_id=3, recurso_id=10).first()
        inv12 = db.query(Inventario).filter_by(ong_id=3, recurso_id=12).first()
        assert inv10.cantidad_disponible == 100
        assert inv12.cantidad_disponible == 30

        # Compromisos de ONG 3 pasaron a LIBERADO
        comps = db.query(CompromisoRecurso).filter_by(id_emergencia=101, id_ong=3).all()
        for c in comps:
            assert c.estado == EstadoCompromiso.LIBERADO
            assert c.fecha_liberacion is not None

        # Compromiso de ONG 9 sigue COMPROMETIDO
        comp_ong9 = db.query(CompromisoRecurso).filter_by(id_emergencia=101, id_ong=9).first()
        assert comp_ong9.estado == EstadoCompromiso.COMPROMETIDO


def test_liberar_sin_compromisos_retorna_404(test_env):
    client, _, token = test_env
    payload = {
        "id_emergencia": 999,
        "id_ong": 3,
        "motivo_cierre": "cierre_sin_recursos",
        "recursos_a_liberar": [{"id_recurso": 10, "cantidad_liberada": 1}],
    }
    res = client.post(
        "/api/v1/proyectos/liberar-recursos",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


def test_liberar_recibe_string_largo_bonita(test_env):
    import json
    client, session_factory, token = test_env
    ahora = datetime.now(timezone.utc)
    with session_factory() as db:
        db.add(Inventario(ong_id=4, recurso_id=30, cantidad_total=50, cantidad_disponible=10))
        db.add(
            CompromisoRecurso(
                id_emergencia=777,
                id_oferta=5,
                id_ong=4,
                id_recurso=30,
                cantidad_comprometida=40,
                estado=EstadoCompromiso.COMPROMETIDO,
                fecha_bloqueo=ahora,
            )
        )
        db.commit()

    payload_str = json.dumps({"id_emergencia": 777, "id_ong": 4, "motivo_cierre": "fin_operativo", "recursos_a_liberar": [{"id_recurso": 30, "cantidad_liberada": 40}]})

    res = client.post(
        "/api/v1/proyectos/liberar-recursos",
        content=payload_str,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
    )
    assert res.status_code == 200
    data = json.loads(res.text)
    assert data["estado"] == "liberacion_exitosa"
    assert data["id_ong"] == 4
    assert data["total_recursos_liberados"] == 40

