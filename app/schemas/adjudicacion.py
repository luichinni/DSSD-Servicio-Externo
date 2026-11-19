from app.core.timezone import ahora_ar
from typing import Any, Literal

from pydantic import AwareDatetime, ConfigDict, Field, field_validator, model_validator

from app.core.deserializer import deserializar_json_string

from app.schemas.common import (
    ApiModel,
    Cantidad,
    IdEmergencia,
    IdOferta,
    IdOng,
    IdRecurso,
    validar_sin_duplicados,
)

# Se define el esquema de request y response para el endpoint de adjudicación de ofertas: POST /api/v1/ofertas/adjudicar.
# Errores documentados en la ruta: 401, 404 y 409 (inventario insuficiente -> rollback).

# --- Request -----------------------------------------------------------------
class RecursoAdjudicado(ApiModel):
    id_recurso: IdRecurso
    cantidad_adjudicada: Cantidad


class OfertaAdjudicada(ApiModel):
    id_oferta: IdOferta
    id_ong: IdOng
    recursos: list[RecursoAdjudicado] = Field(min_length=1)

    @field_validator("recursos")
    @classmethod
    def _recursos_sin_duplicados(cls, v: list[RecursoAdjudicado]) -> list[RecursoAdjudicado]:
        validar_sin_duplicados((r.id_recurso for r in v), "id_recurso")
        return v


class AdjudicarOfertasRequest(ApiModel):
    id_emergencia: IdEmergencia
    ofertas_adjudicadas: list[OfertaAdjudicada] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _deserializar_si_es_string(cls, data: Any) -> Any:
        # Bonita puede enviar el JSON serializado como string.
        return deserializar_json_string(data)

    @field_validator("ofertas_adjudicadas")
    @classmethod
    def _ofertas_sin_duplicados(cls, v: list[OfertaAdjudicada]) -> list[OfertaAdjudicada]:
        validar_sin_duplicados((o.id_oferta for o in v), "id_oferta")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id_emergencia": 101,
                    "ofertas_adjudicadas": [
                        {
                            "id_oferta": 15,
                            "id_ong": 3,
                            "recursos": [{"id_recurso": 10, "cantidad_adjudicada": 50}],
                        }
                    ],
                }
            ]
        }
    )


# --- Response ----------------------------------------------------------------
class RecursoSinStockDetalle(ApiModel):
    id_recurso: IdRecurso
    cantidad_solicitada: int
    cantidad_disponible: int
    motivo: str


class OfertaRechazadaDetalle(ApiModel):
    id_oferta: IdOferta
    id_ong: IdOng
    motivo: str
    recursos_sin_stock: list[RecursoSinStockDetalle] = Field(default_factory=list)


class OfertaAdjudicadaResultado(ApiModel):
    id_oferta: IdOferta
    id_ong: IdOng
    estado: str = "adjudicada"


class AdjudicarOfertasResponse(ApiModel):
    id_emergencia: IdEmergencia
    estado: Literal["bloqueo_exitoso", "bloqueo_parcial"]
    mensaje: str
    timestamp_bloqueo: AwareDatetime = Field(
        description="Momento del commit, en UTC (ahora_ar())."
    )
    ofertas_adjudicadas: list[OfertaAdjudicadaResultado] = Field(
        default_factory=list,
        description="Ofertas efectivamente adjudicadas (opcional).",
    )
    ofertas_rechazadas: list[OfertaRechazadaDetalle] = Field(
        default_factory=list,
        description="Ofertas rechazadas por falta de stock o inconsistencias (opcional).",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id_emergencia": 101,
                    "estado": "bloqueo_exitoso",
                    "mensaje": "Los recursos han sido comprometidos transaccionalmente a nivel nacional.",
                    "timestamp_bloqueo": "2026-10-12T15:30:00Z",
                }
            ]
        }
    )