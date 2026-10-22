from collections.abc import Generator
from datetime import timedelta
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
from app.models.user import User


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def saved_user(client: TestClient) -> tuple[UUID, str]:
    password = "correct-horse-battery-staple"
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        user = User(email="person@example.com", hashed_password=hash_password(password))
        db.add(user)
        db.commit()
        return user.id, password
    finally:
        db_generator.close()


def test_login_returns_token_for_valid_credentials(
    client: TestClient,
    saved_user: tuple[UUID, str],
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": saved_user[1]},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "person@example.com", "password": "incorrect-password"},
        {"email": "missing@example.com", "password": "correct-horse-battery-staple"},
    ],
)
def test_login_rejects_invalid_credentials(
    client: TestClient,
    saved_user: tuple[UUID, str],
    credentials: dict[str, str],
) -> None:
    response = client.post("/api/v1/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_current_user_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token"})

    assert response.status_code == 401


def test_current_user_rejects_expired_token(
    client: TestClient,
    saved_user: tuple[UUID, str],
) -> None:
    token = create_access_token(saved_user[0], expires_delta=timedelta(seconds=-1))

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_current_user_rejects_token_for_missing_user(client: TestClient) -> None:
    token = create_access_token(UUID("00000000-0000-0000-0000-000000000001"))

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_current_user_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_current_user_returns_public_user(
    client: TestClient,
    saved_user: tuple[UUID, str],
) -> None:
    token = create_access_token(saved_user[0])

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": str(saved_user[0]),
        "email": "person@example.com",
    }
    assert "hashed_password" not in response.json()


def test_auth_endpoints_are_documented_in_openapi(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()

    login = openapi["paths"]["/api/v1/auth/login"]["post"]
    assert login["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/LoginRequest"
    )
    assert (
        openapi["paths"]["/api/v1/auth/me"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"].endswith("/UserResponse")
    )
    assert (
        openapi["components"]["securitySchemes"]["OAuth2PasswordBearer"]["scheme"]
        == "bearer"
    )


def test_existing_health_endpoints_remain_available(client: TestClient) -> None:
    api_health = client.get("/health")
    database_health = client.get("/health/db")

    assert api_health.status_code == 200
    assert api_health.json() == {"status": "ok"}
    assert database_health.status_code == 200
    assert database_health.json() == {"status": "ok"}
