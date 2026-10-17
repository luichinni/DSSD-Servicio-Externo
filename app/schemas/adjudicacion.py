from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

from app.core.deserializer import deserializar_json_string


class RecursoAdjudicado(BaseModel):
    id_recurso: Annotated[int, Field(gt=0, description="Identificador único del recurso")]
    cantidad_adjudicada: Annotated[int, Field(gt=0, description="Cantidad a adjudicar y bloquear")]


class OfertaAdjudicadaItem(BaseModel):
    id_oferta: Annotated[int, Field(gt=0, description="Identificador de la oferta")]
    id_ong: Annotated[int, Field(gt=0, description="Identificador de la ONG")]
    recursos: Annotated[list[RecursoAdjudicado], Field(min_length=1, description="Recursos a adjudicar")]


class AdjudicarRequest(BaseModel):
    id_emergencia: Annotated[int, Field(gt=0, description="Identificador de la emergencia")]
    ofertas_adjudicadas: Annotated[
        list[OfertaAdjudicadaItem],
        Field(min_length=1, description="Lista de ofertas a adjudicar"),
    ]

    @model_validator(mode="before")
    @classmethod
    def parse_string_if_needed(cls, data: Any) -> Any:
        return deserializar_json_string(data)



class RecursoSinStockDetalle(BaseModel):
    id_recurso: int
    cantidad_solicitada: int
    cantidad_disponible: int
    motivo: str


class OfertaRechazadaDetalle(BaseModel):
    id_oferta: int
    id_ong: int
    motivo: str
    recursos_sin_stock: list[RecursoSinStockDetalle] = Field(default_factory=list)


class OfertaAdjudicadaResultado(BaseModel):
    id_oferta: int
    id_ong: int
    estado: str = "adjudicada"


class AdjudicarResponse(BaseModel):
    id_emergencia: int
    estado: str
    mensaje: str
    timestamp_bloqueo: datetime
    ofertas_adjudicadas: list[OfertaAdjudicadaResultado] = Field(default_factory=list)
    ofertas_rechazadas: list[OfertaRechazadaDetalle] = Field(default_factory=list)
