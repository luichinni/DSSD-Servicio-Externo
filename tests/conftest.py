from collections.abc import Generator
from os import environ
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User


@pytest.fixture
def entorno(monkeypatch) -> Generator[tuple[TestClient, Session, dict], None, None]:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-key-that-is-at-least-32-bytes-long")
    postgres_url = environ.get("DSSD_TEST_DATABASE_URL")
    schema = None
    if postgres_url:
        engine = create_engine(postgres_url)
        schema = "catalogo_test_" + uuid4().hex
        with engine.begin() as conexion:
            conexion.execute(CreateSchema(schema))
        engine = engine.execution_options(schema_translate_map={None: schema})
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(engine, "connect")
        def activar_referencias(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

    try:
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False) as db:
            user = User(id=uuid4(), email="validacion@example.com", hashed_password="unused")
            db.add(user)
            db.commit()

            def override_db():
                yield db

            app.dependency_overrides[get_db] = override_db
            headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
            try:
                with TestClient(app) as client:
                    yield client, db, headers
            finally:
                app.dependency_overrides.clear()
    finally:
        if schema:
            with engine.begin() as conexion:
                conexion.execute(DropSchema(schema, cascade=True))
        engine.dispose()
