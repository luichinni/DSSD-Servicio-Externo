from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.openapi import TAG_PROYECTOS
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas import LiberarRecursosRequest, LiberarRecursosResponse, errores
from app.services.liberacion import procesar_liberacion

"""Endpoints de proyectos.
La firma (ruta, body, response_model, errores) es el contrato; no cambiarla sin avisar. Se registra en main.py con prefix="/api/v1".
"""

router = APIRouter(tags=[TAG_PROYECTOS], dependencies=[Depends(get_current_user)])


@router.post(
    "/proyectos/liberar-recursos",
    response_model=LiberarRecursosResponse,
    responses=errores(401, 404),
    summary="Liberar recursos al cerrar un proyecto",
    description="Marca el fin de actividades: devuelve al inventario disponible los recursos "
    "comprometidos para la emergencia y la ONG indicadas, dentro de una transacción. "
    "Requiere JWT.",
)
def liberar_recursos(
    payload: LiberarRecursosRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LiberarRecursosResponse:
    return procesar_liberacion(db=db, request=payload)