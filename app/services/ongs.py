from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ONG
from app.schemas.ong import ONGCreate


class OngYaRegistrada(ValueError):
    pass


def registrar_ong(datos: ONGCreate, db: Session) -> ONG:
    if db.get(ONG, datos.id_ong) is not None:
        raise OngYaRegistrada(f"La ONG {datos.id_ong} ya está registrada.")
    nueva_ong = ONG(
        id=datos.id_ong,
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        habilitada=True,
    )
    db.add(nueva_ong)
    db.commit()
    db.refresh(nueva_ong)
    return nueva_ong


def listar_ongs(db: Session) -> list[ONG]:
    return list(db.scalars(
        select(ONG).where(ONG.habilitada.is_(True)).order_by(ONG.nombre, ONG.id)
    ).all())
