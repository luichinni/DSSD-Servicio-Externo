from pydantic import ConfigDict, Field

from app.schemas.common import ApiModel, IdOng, IdRecurso

#----- Se definen los esquemas de error y helper para documentarlos en Swagger------

# Define el formato estándar de HTTPException en FastAPI para errores comunes (como 400, 401, 404) heredando de ApiModel
class ErrorResponse(ApiModel):
    """FastAPI, cuando lanzás una excepción nativa (raise HTTPException(status_code=..., detail="...")), devuelve por defecto un JSON con la clave detail"""
    detail: str = Field(description="Descripción del error.")

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"detail": "Token inválido o expirado"}]}
    )

#Modela el objeto interno que explica con precisión por qué falló la adjudicación por falta de stock.
class ConflictoInventarioDetalle(ApiModel):
    """Detalle del 409: el inventario no alcanza para la cantidad adjudicada."""
    mensaje: str
    id_ong: IdOng
    id_recurso: IdRecurso
    cantidad_solicitada: int = Field(ge=0, description="Cantidad que se intentó bloquear.")
    inventario_disponible: int = Field(ge=0, description="Inventario real al momento del bloqueo.")


class ConflictoInventarioResponse(ApiModel):
    """HTTP 409. Dev 5 lo levanta con ``HTTPException(409, detail=ConflictoInventarioDetalle(...).model_dump())``."""

    detail: ConflictoInventarioDetalle

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "detail": {
                        "mensaje": "Inventario insuficiente; se hizo rollback de toda la adjudicación.",
                        "id_ong": 3,
                        "id_recurso": 10,
                        "cantidad_solicitada": 50,
                        "inventario_disponible": 30,
                    }
                }
            ]
        }
    )

# Asocia cada código de error HTTP con su modelo y descripción para documentar en Swagger. 
# FastAPI documenta automáticamente el 422 de validación (cuando falla un tipo de dato pydantic)(``HTTPValidationError``), por eso no se redefine acá. 
_RESPUESTAS: dict[int, dict] = {
    400: {"model": ErrorResponse, "description": "Solicitud inválida o estado de negocio inconsistente."},
    401: {"model": ErrorResponse, "description": "Token JWT ausente, inválido o expirado."},
    404: {"model": ErrorResponse, "description": "ONG, recurso, oferta o emergencia inexistente."},
    409: {
        "model": ConflictoInventarioResponse,
        "description": "Conflicto de inventario: no alcanza el stock (se hace rollback).",
    },
}

#Helper para documentar en Swagger los códigos de error que puede devolver una ruta. Ejemplo de uso: si una ruta puede devolver 400, 401 y 404, ``@router.post(..., responses=errores(400, 401, 404))``.
# Básicamente, en cada endpoint, se le pasa a FastAPI este dict para que documente en Swagger los códigos de error que puede devolver la ruta.
def errores(*codigos: int) -> dict[int, dict]:
    """Devuelve el dict para el parámetro ``responses=`` de una ruta."""
    return {codigo: _RESPUESTAS[codigo] for codigo in codigos}