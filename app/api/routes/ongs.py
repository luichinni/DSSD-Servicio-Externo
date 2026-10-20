from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.ong import ONGCreate, ONGResponse
from app.services.ongs import registrar_ong, listar_ongs
from app.db.session import get_db

router = APIRouter(prefix="/ongs", tags=["ONGs"])
DatabaseSession = Annotated[Session, Depends(get_db)]

@router.post("/", response_model=ONGResponse, status_code=status.HTTP_201_CREATED)
def crear_ong(datos: ONGCreate, db: DatabaseSession):
    try:
        return registrar_ong(datos, db)
    except Exception:
        db.rollback()
        raise

@router.get("/", response_model=list[ONGResponse])
def obtener_ongs(db: DatabaseSession):
    return listar_ongs(db)