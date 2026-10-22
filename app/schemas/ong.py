from pydantic import Field

from app.schemas.catalogo import OngHabilitada
from app.schemas.common import ApiModel, IdOng


class ONGCreate(ApiModel):
    id_ong: IdOng = Field(description="ID ya asignado por la app local; no se genera otro.")
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None


ONGResponse = OngHabilitada
