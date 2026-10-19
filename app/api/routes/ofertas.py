from fastapi import APIRouter, HTTPException, status

from app.core.openapi import TAG_OFERTAS
from app.schemas import (
    AdjudicarOfertasRequest,
    AdjudicarOfertasResponse,
    ValidarOfertasRequest,
    ValidarOfertasResponse,
    errores,
)

"""Endpoints de ofertas. ESQUELETO de Dev 2: Dev 4 implementa /validar y Dev 5 /adjudicar.
La firma (ruta, body, response_model, errores) es el contrato; no cambiarla sin avisar. Se registra en main.py con prefix="/api/v1".
"""

# Seguridad: agregar dependencies=[Depends(get_current_user)] en la integración final.
router = APIRouter(tags=[TAG_OFERTAS])


@router.post(
    "/ofertas/validar",
    response_model=ValidarOfertasResponse,
    responses=errores(401, 404),
    summary="Validar ofertas por competencias",
    description="Cruza cada recurso ofrecido con las certificaciones de la ONG y asigna perfil "
    "de competencia, nivel de riesgo y clasificación por recurso. No hay rechazo binario. "
    "Requiere JWT.",
)
def validar_ofertas(payload: ValidarOfertasRequest):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Pendiente de implementación (Dev 4)")


@router.post(
    "/ofertas/adjudicar",
    response_model=AdjudicarOfertasResponse,
    responses=errores(401, 404, 409),
    summary="Adjudicar ofertas y bloquear recursos",
    description="Bloquea transaccionalmente (with_for_update) los recursos de las ofertas elegidas "
    "y los asocia a la emergencia. Si el inventario no alcanza, responde 409 y hace rollback "
    "de toda la adjudicación. Requiere JWT.",
)
def adjudicar_ofertas(payload: AdjudicarOfertasRequest):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Pendiente de implementación (Dev 5)")