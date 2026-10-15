from functools import lru_cache
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DatabaseConfigurationError, get_database_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_database_url(), pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    try:
        db = get_session_factory()()
    except DatabaseConfigurationError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseConfigurationError(
            "No se pudo inicializar SQLAlchemy. Verificá el formato de DATABASE_URL."
        ) from exc

    try:
        yield db
    finally:
        db.close()
