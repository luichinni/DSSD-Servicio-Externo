import os
from dataclasses import dataclass


class DatabaseConfigurationError(RuntimeError):
    pass


class JWTConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class JWTSettings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise DatabaseConfigurationError(
            "DATABASE_URL no está configurada. Configurá la URL de PostgreSQL "
            "en el archivo .env."
        )
    # SQLAlchemy usa psycopg2 por defecto para estas URLs; el proyecto instala psycopg 3.
    for prefix in ("postgresql://", "postgres://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix):]
    return database_url


def get_jwt_settings() -> JWTSettings:
    secret_key = os.getenv("JWT_SECRET_KEY", "")
    if len(secret_key.encode("utf-8")) < 32:
        raise JWTConfigurationError(
            "JWT_SECRET_KEY debe contener al menos 32 bytes aleatorios."
        )

    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    if algorithm not in {"HS256", "HS384", "HS512"}:
        raise JWTConfigurationError(
            "JWT_ALGORITHM debe ser uno de: HS256, HS384 o HS512."
        )

    try:
        expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    except ValueError as exc:
        raise JWTConfigurationError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe ser un entero positivo."
        ) from exc

    if expire_minutes <= 0:
        raise JWTConfigurationError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe ser un entero positivo."
        )

    return JWTSettings(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=expire_minutes,
    )
