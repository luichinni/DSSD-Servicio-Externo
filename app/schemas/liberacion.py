from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

from app.core.deserializer import deserializar_json_string


class RecursoALiberar(BaseModel):
    id_recurso: Annotated[int, Field(gt=0, description="Identificador único del recurso")]
    cantidad_liberada: Annotated[int, Field(gt=0, description="Cantidad que se solicita liberar")]


class LiberarRequest(BaseModel):
    id_emergencia: Annotated[int, Field(gt=0, description="Identificador de la emergencia")]
    id_ong: Annotated[int, Field(gt=0, description="Identificador de la ONG")]
    motivo_cierre: Annotated[str, Field(default="finalizacion_tareas", description="Motivo del cierre o liberación")]
    recursos_a_liberar: Annotated[
        list[RecursoALiberar],
        Field(default_factory=list, description="Lista opcional de recursos informados a liberar"),
    ]

    @model_validator(mode="before")
    @classmethod
    def parse_string_if_needed(cls, data: Any) -> Any:
        return deserializar_json_string(data)



class LiberarResponse(BaseModel):
    estado: str = "liberacion_exitosa"
    id_ong: int
    mensaje: str = "Recursos liberados. Disponibilidad global actualizada."
    total_recursos_liberados: int = 0
