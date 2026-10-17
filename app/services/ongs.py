from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import ONG
from app.schemas.ong import ONGCreate

def registrar_ong(datos: ONGCreate, db: Session) -> ONG:
    nueva_ong = ONG(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        habilitada=True
    )

    if not nueva_ong.nombre:
        raise ValueError("El nombre de la ONG no puede estar vacío.")

    db.add(nueva_ong)
    db.commit()
    db.refresh(nueva_ong)
    return nueva_ong

def listar_ongs(db: Session) -> list[ONG]:
    consulta = (select(ONG).order_by(ONG.nombre.asc()).where(ONG.habilitada == True))

    return db.list(db.scalars(consulta).all())