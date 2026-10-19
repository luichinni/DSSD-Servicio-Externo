from fastapi import APIRouter, HTTPException, Query, status

from app.core.openapi import TAG_CATALOGO
from app.schemas import DisponibilidadResponse, OngsHabilitadasResponse, errores

"""Endpoints del catálogo. ESQUELETO de Dev 2: Dev 3 reemplaza el cuerpo de cada función.
La firma (ruta, parámetros, response_model, errores) es el contrato; no cambiarla sin avisar. Se registra en main.py con prefix="/api/v1".
"""

# Seguridad: agregar dependencies=[Depends(get_current_user)] en la integración final.
router = APIRouter(tags=[TAG_CATALOGO])


@router.get(
    "/ongs/habilitadas",
    response_model=OngsHabilitadasResponse,
    responses=errores(401),
    summary="Listar ONGs y su estado de habilitación",
    description="Devuelve las ONGs registradas en el Sistema Nacional con su estado de "
    "habilitación y sus certificaciones. Requiere JWT.",
)
def listar_ongs_habilitadas():
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Pendiente de implementación (Dev 3)")


@router.get(
    "/recursos/disponibilidad",
    response_model=DisponibilidadResponse,
    responses=errores(401),
    summary="Consultar disponibilidad global de recursos",
    description="Devuelve el inventario disponible y la cantidad comprometida por ONG y recurso. "
    "Permite filtrar por recurso y/o ONG. Requiere JWT.",
)
def consultar_disponibilidad(
    recurso_id: int | None = Query(default=None, gt=0, description="Filtrar por recurso.", examples=[10]),
    id_ong: int | None = Query(default=None, gt=0, description="Filtrar por ONG.", examples=[3]),
):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Pendiente de implementación (Dev 3)")