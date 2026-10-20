from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.catalogo import consultar_disponibilidad
from app.schemas.catalogo import RecursoDisponibleResponse

router = APIRouter(prefix="/catalogo", tags=["Catalogo"])
DatabaseSession = Annotated[Session, Depends(get_db)]

@router.get("/disponibilidad", response_model=list[RecursoDisponibleResponse])
def obtener_disponibilidad(db: DatabaseSession):
    return consultar_disponibilidad(db)