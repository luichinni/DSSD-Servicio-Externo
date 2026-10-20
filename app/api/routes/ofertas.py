from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import DatabaseConfigurationError
from app.core.openapi import TAG_OFERTAS
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas import (
    AdjudicarOfertasRequest,
    AdjudicarOfertasResponse,
    ValidarOfertasRequest,
    ValidarOfertasResponse,
    errores,
)
from app.services.validacion import (
    CertificacionNoEncontrada,
    ReferenciaNoDisponible,
    consultar_certificaciones,
    evaluar_ofertas,
)

router = APIRouter(tags=[TAG_OFERTAS], dependencies=[Depends(get_current_user)])


@router.post(
    "/ofertas/validar",
    response_model=ValidarOfertasResponse,
    responses={**errores(401, 404), 503: {"description": "Registro nacional no disponible."}},
    summary="Validar ofertas por competencias",
    description=(
        "Evalúa cada recurso con certificaciones vigentes y devuelve principal o apoyo. "
        "El apoyo se limita al nivel de riesgo informado y requiere supervisión. "
        "Para ofertas conjuntas se puede enviar un participante por solicitud. "
        "No verifica stock ni reserva recursos. Requiere JWT."
    ),
)
def validar_ofertas(
    payload: ValidarOfertasRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ValidarOfertasResponse:
    try:
        certificaciones = consultar_certificaciones(db, payload)
    except ReferenciaNoDisponible as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise DatabaseConfigurationError("No se pudo consultar el registro de certificaciones.") from exc
    try:
        return evaluar_ofertas(payload, certificaciones, datetime.now(timezone.utc).date())
    except CertificacionNoEncontrada as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/ofertas/adjudicar",
    response_model=AdjudicarOfertasResponse,
    responses=errores(401, 404, 409),
    summary="Adjudicar ofertas y bloquear recursos",
    description="Esqueleto de Dev 2; implementación transaccional pendiente de Dev 5.",
)
def adjudicar_ofertas(payload: AdjudicarOfertasRequest):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Pendiente de implementación (Dev 5)")
