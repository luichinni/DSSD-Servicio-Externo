from pydantic import ConfigDict, Field

from app.schemas.common import ApiModel, IdOng, IdRecurso

# --- Se definen los esquemas de respuesta para los endpoints de catálogo:
# GET /api/v1/ongs/habilitadas
# GET /api/v1/recursos/disponibilidad     (filtros por query param: ?recurso_id=10&id_ong=3)

# --- ONGs --------------------------------------------------------------------
class OngHabilitada(ApiModel):
    id_ong: IdOng
    nombre: str = Field(min_length=1, max_length=150, examples=["Cruz Roja Regional Norte"])
    habilitada: bool = Field(description="True si la ONG está habilitada en el Sistema Nacional.")
    #Las certificaciones las tome como una lista de texto, si no tiene devuelve una lista vacía.
    certificaciones: list[str] = Field(
        default_factory=list,
        description="Certificaciones vigentes de la ONG.",
        examples=[["Rescate acuático", "Logística de emergencias"]],
    )

#En lugar de devolver una lista de ONGs crudas, se devuelve un objeto con la cantidad total y la lista de ONGs.
class OngsHabilitadasResponse(ApiModel):
    total: int = Field(ge=0, description="Cantidad de ONGs devueltas.")
    ongs: list[OngHabilitada]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total": 1,
                    "ongs": [
                        {
                            "id_ong": 3,
                            "nombre": "Cruz Roja Regional Norte",
                            "habilitada": True,
                            "certificaciones": ["Rescate acuático", "Logística de emergencias"],
                        }
                    ],
                }
            ]
        }
    )


# --- Disponibilidad de recursos ---------------------------------------------
class RecursoDisponible(ApiModel):
    id_ong: IdOng
    id_recurso: IdRecurso
    nombre_recurso: str = Field(min_length=1, max_length=150, examples=["Bote inflable"])
    inventario_actual: int = Field(ge=0, description="Unidades disponibles hoy.", examples=[120])
    cantidad_comprometida: int = Field(
        default=0, ge=0, description="Unidades bloqueadas por adjudicaciones vigentes.", examples=[50]
    )


class DisponibilidadResponse(ApiModel):
    total: int = Field(ge=0)
    recursos: list[RecursoDisponible]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total": 1,
                    "recursos": [
                        {
                            "id_ong": 3,
                            "id_recurso": 10,
                            "nombre_recurso": "Bote inflable",
                            "inventario_actual": 120,
                            "cantidad_comprometida": 50,
                        }
                    ],
                }
            ]
        }
    )