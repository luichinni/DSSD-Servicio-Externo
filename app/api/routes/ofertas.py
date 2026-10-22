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
from app.services.adjudicacion import procesar_adjudicacion
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
    description=(
        "Verifica y descuenta el inventario disponible dentro de una transacción con bloqueo de filas. "
        "Si ninguna oferta puede adjudicarse devuelve 409 con rollback; si alcanza solo para algunas, "
        "adjudica esas y devuelve el detalle de las rechazadas. Requiere JWT."
    ),
)
def adjudicar_ofertas(
    payload: AdjudicarOfertasRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AdjudicarOfertasResponse:
    respuesta, _ = procesar_adjudicacion(db=db, request=payload)
    return respuesta
