from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import DatabaseConfigurationError
from app.core.openapi import TAG_CATALOGO
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas import DisponibilidadResponse, OngsHabilitadasResponse, errores
from app.services.catalogo import consultar_disponibilidad, consultar_ongs_habilitadas
from app.core.timezone import ahora_ar

router = APIRouter(tags=[TAG_CATALOGO], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[Session, Depends(get_db)]
respuestas = {**errores(401), 503: {"description": "Catálogo nacional no disponible."}}


@router.get(
    "/ongs/habilitadas", response_model=OngsHabilitadasResponse,
    responses=respuestas, summary="Consultar ONGs habilitadas y sus certificaciones vigentes",
)
def obtener_ongs_habilitadas(db: DatabaseSession):
    try:
        ongs = consultar_ongs_habilitadas(db, ahora_ar().date())
    except SQLAlchemyError as exc:
        raise DatabaseConfigurationError("No se pudo consultar el catálogo de ONGs.") from exc
    return OngsHabilitadasResponse(total=len(ongs), ongs=ongs)


@router.get(
    "/recursos/disponibilidad", response_model=DisponibilidadResponse,
    responses=respuestas, summary="Consultar disponibilidad por ONG y recurso",
)
def obtener_disponibilidad(
    db: DatabaseSession,
    recurso_id: int | None = Query(default=None, gt=0),
    id_ong: int | None = Query(default=None, gt=0),
):
    try:
        recursos = consultar_disponibilidad(db, recurso_id=recurso_id, id_ong=id_ong)
    except SQLAlchemyError as exc:
        raise DatabaseConfigurationError("No se pudo consultar el inventario nacional.") from exc
    return DisponibilidadResponse(total=len(recursos), recursos=recursos)
