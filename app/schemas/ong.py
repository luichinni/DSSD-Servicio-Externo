import uuid
from pydantic import BaseModel, ConfigDict, Field

class ONGCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = None

class ONGResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    descripcion: str | None
    habilitada: bool