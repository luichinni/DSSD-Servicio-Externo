from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.core.deserializer import deserializar_json_string

from app.schemas.common import (
    ApiModel,
    Cantidad,
    IdEmergencia,
    IdOng,
    IdRecurso,
    validar_sin_duplicados,
)

# Se define el esquema de request y response para el endpoint de liberación de recursos: POST /api/v1/proyectos/liberar-recursos.
# Errores documentados en la ruta: 401 y 404 (no hay recursos comprometidos para ese id_emergencia / id_ong).

# --- Request -----------------------------------------------------------------
class RecursoALiberar(ApiModel):
    id_recurso: IdRecurso
    cantidad_liberada: Cantidad


class LiberarRecursosRequest(ApiModel):
    id_emergencia: IdEmergencia
    id_ong: IdOng
    motivo_cierre: str = Field(min_length=1, max_length=50, examples=["finalizacion_tareas"])
    recursos_a_liberar: list[RecursoALiberar] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _deserializar_si_es_string(cls, data: Any) -> Any:
        # Bonita puede enviar el JSON serializado como string.
        return deserializar_json_string(data)

    @field_validator("recursos_a_liberar")
    @classmethod
    def _recursos_sin_duplicados(cls, v: list[RecursoALiberar]) -> list[RecursoALiberar]:
        validar_sin_duplicados((r.id_recurso for r in v), "id_recurso")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id_emergencia": 101,
                    "id_ong": 3,
                    "motivo_cierre": "finalizacion_tareas",
                    "recursos_a_liberar": [{"id_recurso": 10, "cantidad_liberada": 50}],
                }
            ]
        }
    )


# --- Response ----------------------------------------------------------------
class LiberarRecursosResponse(ApiModel):
    estado: Literal["liberacion_exitosa"]
    id_ong: IdOng
    mensaje: str
    total_recursos_liberados: int = Field(
        default=0, description="Unidades liberadas en total (opcional)."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "estado": "liberacion_exitosa",
                    "id_ong": 3,
                    "mensaje": "Recursos liberados. Disponibilidad global actualizada.",
                }
            ]
        }
    )