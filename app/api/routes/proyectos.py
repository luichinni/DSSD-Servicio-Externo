from fastapi import APIRouter, HTTPException, status

from app.core.openapi import TAG_PROYECTOS
from app.schemas import LiberarRecursosRequest, LiberarRecursosResponse, errores

"""Endpoints de proyectos. ESQUELETO de Dev 2: Dev 5 reemplaza el cuerpo.
La firma (ruta, body, response_model, errores) es el contrato; no cambiarla sin avisar. Se registra en main.py con prefix="/api/v1".
"""

# Seguridad: agregar dependencies=[Depends(get_current_user)] en la integración final.
router = APIRouter(tags=[TAG_PROYECTOS])


@router.post(
    "/proyectos/liberar-recursos",
    response_model=LiberarRecursosResponse,
    responses=errores(401, 404),
    summary="Liberar recursos al cerrar un proyecto",
    description="Marca el fin de actividades: devuelve al inventario disponible los recursos "
    "comprometidos para la emergencia y la ONG indicadas, dentro de una transacción. "
    "Requiere JWT.",
)
def liberar_recursos(payload: LiberarRecursosRequest):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Pendiente de implementación (Dev 5)")