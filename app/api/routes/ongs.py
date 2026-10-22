from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import DatabaseConfigurationError
from app.core.openapi import TAG_CATALOGO
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.errors import ErrorResponse, errores
from app.schemas.ong import ONGCreate, ONGResponse
from app.services.ongs import OngYaRegistrada, registrar_ong

router = APIRouter(prefix="/ongs", tags=[TAG_CATALOGO], dependencies=[Depends(get_current_user)])


@router.post(
    "", response_model=ONGResponse, status_code=status.HTTP_201_CREATED,
    summary="Registrar una ONG con su ID de la app local",
    responses={
        **errores(401),
        409: {"model": ErrorResponse, "description": "ID de ONG ya registrado."},
        503: {"description": "Catálogo nacional no disponible."},
    },
)
def crear_ong(datos: ONGCreate, db: Annotated[Session, Depends(get_db)]):
    try:
        ong = registrar_ong(datos, db)
    except (OngYaRegistrada, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El ID de ONG ya está registrado.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise DatabaseConfigurationError("No se pudo registrar la ONG.") from exc
    return ONGResponse(id_ong=ong.id, nombre=ong.nombre, habilitada=ong.habilitada, certificaciones=[])
