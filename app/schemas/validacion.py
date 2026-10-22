from enum import StrEnum
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.core.deserializer import deserializar_json_string
from app.schemas.common import (
    ApiModel,
    Cantidad,
    GravedadCampo,
    IdEmergencia,
    IdOferta,
    IdOng,
    IdRecurso,
    TipoDesastreCampo,
    validar_sin_duplicados,
)

# --- Se define el esquema de request y response para el endpoint de validación de ofertas: POST /api/v1/ofertas/validar.
# Bonita envía las ofertas; la API devuelve, por oferta, un perfil de competencia y un nivel de riesgo (NO un rechazo binario, según el enunciado).


# --- Enums de SALIDA (los genera nuestra API, no hay riesgo de rechazar a Bonita)
class ClasificacionRecurso(StrEnum):
    LOTE_PRINCIPAL = "lote_principal"
    APOYO_SECUNDARIO = "apoyo_secundario"


class PerfilCompetencia(StrEnum):
    BASICO = "Basico"
    INTERMEDIO = "Intermedio"
    AVANZADO = "Avanzado"


class NivelRiesgo(StrEnum):
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"


# --- Request -----------------------------------------------------------------
class RecursoOfertado(ApiModel):
    id_recurso: IdRecurso
    cantidad_ofrecida: Cantidad


class OfertaEntrada(ApiModel):
    id_oferta: IdOferta
    es_conjunta: bool = Field(description="True si la oferta es conjunta entre ONGs.")
    id_ong: IdOng
    recursos: list[RecursoOfertado] = Field(min_length=1, description="Al menos un recurso.")

    @field_validator("recursos")
    @classmethod
    def _recursos_sin_duplicados(cls, v: list[RecursoOfertado]) -> list[RecursoOfertado]:
        validar_sin_duplicados((r.id_recurso for r in v), "id_recurso")
        return v


class ValidarOfertasRequest(ApiModel):
    id_emergencia: IdEmergencia
    tipo_desastre: TipoDesastreCampo
    gravedad: GravedadCampo
    ofertas: list[OfertaEntrada] = Field(min_length=1, description="Al menos una oferta.")

    @model_validator(mode="before")
    @classmethod
    def _deserializar_si_es_string(cls, data: Any) -> Any:
        return deserializar_json_string(data)

    @field_validator("ofertas")
    @classmethod
    def _ofertas_sin_duplicados(cls, v: list[OfertaEntrada]) -> list[OfertaEntrada]:
        validar_sin_duplicados((o.id_oferta for o in v), "id_oferta")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id_emergencia": 101,
                    "tipo_desastre": "hidrologico",
                    "gravedad": "alto",
                    "ofertas": [
                        {
                            "id_oferta": 15,
                            "es_conjunta": False,
                            "id_ong": 3,
                            "recursos": [
                                {"id_recurso": 10, "cantidad_ofrecida": 50},
                                {"id_recurso": 12, "cantidad_ofrecida": 5},
                            ],
                        }
                    ],
                }
            ]
        }
    )


# --- Response ----------------------------------------------------------------
class RecursoEvaluado(ApiModel):
    id_recurso: IdRecurso
    cantidad_validada: int = Field(ge=0, description="Cantidad aceptada tras la evaluación.")
    clasificacion: ClasificacionRecurso
    observacion: str | None = Field(default=None, max_length=255)


class OfertaValidada(ApiModel):
    id_oferta: IdOferta
    id_ong: IdOng
    perfil_competencia_ong: PerfilCompetencia
    nivel_riesgo_permitido: NivelRiesgo
    recursos_evaluados: list[RecursoEvaluado]


class ValidarOfertasResponse(ApiModel):
    id_emergencia: IdEmergencia
    estado_general: Literal["validado"]
    ofertas_validadas: list[OfertaValidada]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id_emergencia": 101,
                    "estado_general": "validado",
                    "ofertas_validadas": [
                        {
                            "id_oferta": 15,
                            "id_ong": 3,
                            "perfil_competencia_ong": "Avanzado",
                            "nivel_riesgo_permitido": "Alto",
                            "recursos_evaluados": [
                                {
                                    "id_recurso": 10,
                                    "cantidad_validada": 50,
                                    "clasificacion": "lote_principal",
                                    "observacion": "Capacidad óptima",
                                },
                                {
                                    "id_recurso": 12,
                                    "cantidad_validada": 5,
                                    "clasificacion": "apoyo_secundario",
                                    "observacion": "Requiere supervisión regional",
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    )