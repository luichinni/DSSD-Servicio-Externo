import unicodedata
from collections.abc import Iterable
from enum import StrEnum
from typing import Annotated
 
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# --- Se definen los tipos base/reutilizables por todos los schemas de la API externa ------------------------
# Los IDs se definen como enteros positivos (mayores a 0)
IdEmergencia = Annotated[
    int,
    Field(gt=0, description="ID de la emergencia (BD local del Municipio).", examples=[101]),
]
IdOferta = Annotated[
    int,
    Field(gt=0, description="ID de la oferta presentada por la ONG.", examples=[15]),
]
IdOng = Annotated[
    int,
    Field(gt=0, description="ID de la ONG.", examples=[3]),
]
IdRecurso = Annotated[
    int,
    Field(gt=0, description="ID del recurso.", examples=[10]),
]
Cantidad = Annotated[
    int,
    Field(gt=0, description="Cantidad en unidades enteras. Debe ser mayor a 0.", examples=[50]),
]


# --- Modelo base de todos los esquemas  -------------------------------------------------------------
class ApiModel(BaseModel):
    """
    - extra="forbid": si en el JSON se envia un campo desconocido, la API rechaza y devuelve 422.
    - str_strip_whitespace: limpia automáticamente los espacios en blanco sobrantes en los strings.
    - from_attributes: permite convertir un objeto de clase a un modelo Pydantic
    """
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        from_attributes=True,
    )


# --- Helpers de validación ---------------------------------------------------
def validar_sin_duplicados(valores: Iterable[int], campo: str) -> None:
    """Lanza ValueError si hay IDs repetidos (FastAPI lo traduce a 422)."""
    vistos: set[int] = set()
    repetidos: set[int] = set()
    for valor in valores:
        if valor in vistos:
            repetidos.add(valor)
        vistos.add(valor)
    if repetidos:
        raise ValueError(f"{campo} duplicado(s): {sorted(repetidos)}")


# --- Enums de dominio compartidos con la app Flask -----------------------------
# Esta función se usa como BeforeValidator en los campos de tipo Enum, para normalizar el texto ingresado por el usuario.
# La API externa permite recibir valores con mayúsculas, espacios y tildes, pero los normaliza a minúsculas y sin tildes para que coincidan con los valores del Enum.
def _normalizar(valor: object) -> object:
    """'Geológico', ' GEOLOGICO ' e 'Incendio Forestal' -> 'geologico', 'incendio_forestal'."""
    if not isinstance(valor, str):
        return valor  # no-strings (ej. 3) caen al Enum y dan 422
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", valor) if unicodedata.category(c) != "Mn"
    )
    return "_".join(sin_tildes.strip().lower().split())
 
 
class TipoDesastre(StrEnum):
    GEOLOGICO = "geologico"
    METEOROLOGICO = "meteorologico"
    HIDROLOGICO = "hidrologico"
    BIOLOGICO = "biologico"
    INCENDIO_FORESTAL = "incendio_forestal"
 
 
class Gravedad(StrEnum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"
 
    @property
    def nivel(self) -> int:
        """Equivalente numérico para mapear a ``nivel_gravedad`` de la BD local."""
        return _NIVEL_GRAVEDAD[self]
 
 
_NIVEL_GRAVEDAD = {
    Gravedad.BAJO: 1,
    Gravedad.MEDIO: 2,
    Gravedad.ALTO: 3,
    Gravedad.CRITICO: 4,
}
 
# Tipos listos para usar en los demás schemas
TipoDesastreCampo = Annotated[
    TipoDesastre,
    BeforeValidator(_normalizar),
    Field(description="Tipo de desastre.", examples=["hidrologico"]),
]
GravedadCampo = Annotated[
    Gravedad,
    BeforeValidator(_normalizar),
    Field(description="Gravedad de la emergencia (texto; 1=bajo ... 4=critico).", examples=["alto"]),
]
 