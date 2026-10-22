from collections.abc import Generator
from datetime import datetime, timezone
from uuid import UUID

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

    # Crear usuario y token para los requests
    with test_session_factory() as db:
        user = User(email="operador@emergencias.gob.ar", hashed_password=hash_password("secreto123"))
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    with TestClient(app) as client:
        yield client, test_session_factory, token

    app.dependency_overrides.clear()
    engine.dispose()


def test_adjudicar_requiere_autenticacion(test_env):
    client, _, _ = test_env
    res = client.post(
        "/api/v1/ofertas/adjudicar",
        json={"id_emergencia": 101, "ofertas_adjudicadas": [{"id_oferta": 1, "id_ong": 3, "recursos": [{"id_recurso": 10, "cantidad_adjudicada": 5}]}]},
    )
    assert res.status_code == 401


def test_adjudicar_exitoso_todo(test_env):
    client, session_factory, token = test_env
    with session_factory() as db:
        db.add(Inventario(ong_id=3, recurso_id=10, cantidad_total=100, cantidad_disponible=100))
        db.add(Inventario(ong_id=3, recurso_id=12, cantidad_total=20, cantidad_disponible=20))
        db.commit()

    payload = {
        "id_emergencia": 101,
        "ofertas_adjudicadas": [
            {
                "id_oferta": 15,
                "id_ong": 3,
                "recursos": [
                    {"id_recurso": 10, "cantidad_adjudicada": 50},
                    {"id_recurso": 12, "cantidad_adjudicada": 5},
                ],
            }
        ],
    }

    res = client.post(
        "/api/v1/ofertas/adjudicar",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id_emergencia"] == 101
    assert data["estado"] == "bloqueo_exitoso"
    assert len(data["ofertas_adjudicadas"]) == 1
    assert len(data["ofertas_rechazadas"]) == 0

    # Verificar BD
    with session_factory() as db:
        inv10 = db.query(Inventario).filter_by(ong_id=3, recurso_id=10).first()
        inv12 = db.query(Inventario).filter_by(ong_id=3, recurso_id=12).first()
        assert inv10.cantidad_disponible == 50
        assert inv12.cantidad_disponible == 15

        comps = db.query(CompromisoRecurso).filter_by(id_emergencia=101, id_oferta=15).all()
        assert len(comps) == 2
        for c in comps:
            assert c.estado == EstadoCompromiso.COMPROMETIDO


def test_adjudicar_idempotente(test_env):
    client, session_factory, token = test_env
    with session_factory() as db:
        db.add(Inventario(ong_id=3, recurso_id=10, cantidad_total=100, cantidad_disponible=100))
        db.commit()

    payload = {
        "id_emergencia": 101,
        "ofertas_adjudicadas": [
            {
                "id_oferta": 15,
                "id_ong": 3,
                "recursos": [{"id_recurso": 10, "cantidad_adjudicada": 40}],
            }
        ],
    }

    # Primera llamada
    res1 = client.post("/api/v1/ofertas/adjudicar", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200

    # Segunda llamada idÃ©ntica
    res2 = client.post("/api/v1/ofertas/adjudicar", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200

    with session_factory() as db:
        inv = db.query(Inventario).filter_by(ong_id=3, recurso_id=10).first()
        # No debe descontar dos veces (100 - 40 = 60)
        assert inv.cantidad_disponible == 60


def test_adjudicar_parcial_ofertas(test_env):
    client, session_factory, token = test_env
    with session_factory() as db:
        db.add(Inventario(ong_id=3, recurso_id=10, cantidad_total=30, cantidad_disponible=30))
        db.add(Inventario(ong_id=5, recurso_id=20, cantidad_total=5, cantidad_disponible=2))
        db.commit()

    payload = {
        "id_emergencia": 202,
        "ofertas_adjudicadas": [
            {
                "id_oferta": 1,
                "id_ong": 3,
                "recursos": [{"id_recurso": 10, "cantidad_adjudicada": 15}],
            },
            {
                "id_oferta": 2,
                "id_ong": 5,
                "recursos": [{"id_recurso": 20, "cantidad_adjudicada": 10}],  # Solo hay 2 disponibles
            },
        ],
    }

    res = client.post("/api/v1/ofertas/adjudicar", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["estado"] == "bloqueo_parcial"
    assert len(data["ofertas_adjudicadas"]) == 1
    assert data["ofertas_adjudicadas"][0]["id_oferta"] == 1
    assert len(data["ofertas_rechazadas"]) == 1
    assert data["ofertas_rechazadas"][0]["id_oferta"] == 2

    with session_factory() as db:
        inv3 = db.query(Inventario).filter_by(ong_id=3, recurso_id=10).first()
        inv5 = db.query(Inventario).filter_by(ong_id=5, recurso_id=20).first()
        assert inv3.cantidad_disponible == 15
        assert inv5.cantidad_disponible == 2  # Intacto


def test_adjudicar_falla_todas_409(test_env):
    client, session_factory, token = test_env
    with session_factory() as db:
        db.add(Inventario(ong_id=3, recurso_id=10, cantidad_total=10, cantidad_disponible=5))
        db.commit()

    payload = {
        "id_emergencia": 303,
        "ofertas_adjudicadas": [
            {
                "id_oferta": 99,
                "id_ong": 3,
                "recursos": [{"id_recurso": 10, "cantidad_adjudicada": 50}],
            }
        ],
    }

    res = client.post("/api/v1/ofertas/adjudicar", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 409
    data = res.json()["detail"]
    assert data["estado"] == "bloqueo_fallido"
    assert len(data["ofertas_rechazadas"]) == 1


def test_adjudicar_recibe_string_largo_bonita(test_env):
    import json
    client, session_factory, token = test_env
    with session_factory() as db:
        db.add(Inventario(ong_id=8, recurso_id=50, cantidad_total=100, cantidad_disponible=100))
        db.commit()

    # Payload enviado como string largo (tal como lo envÃ­a Bonita desde una variable String)
    payload_dict = {
        "id_emergencia": 500,
        "ofertas_adjudicadas": [
            {
                "id_oferta": 1,
                "id_ong": 8,
                "recursos": [{"id_recurso": 50, "cantidad_adjudicada": 25}],
            }
        ],
    }
    string_largo_json = json.dumps(payload_dict)

    # Enviado con content-type text/plain
    res = client.post(
        "/api/v1/ofertas/adjudicar",
        content=string_largo_json,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
    )
    assert res.status_code == 200
    # Verifica que la respuesta de la API es un string largo JSON parseable
    data = json.loads(res.text)
    assert data["estado"] == "bloqueo_exitoso"
    assert data["id_emergencia"] == 500

