from uuid import UUID
import uuid
from pydantic import BaseModel, Field, ConfigDict

class RecursoDisponibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    recurso_id: uuid.UUID
    nombre: str
    unidad_medida: str
    cant_disponible: int
    cant_total: int