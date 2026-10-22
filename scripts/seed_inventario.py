"""Script temporal para poblar Inventario (con sus ONG y Recursos) de prueba."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_database_url
from app.models.inventario import Inventario
from app.models.ong import ONG
from app.models.recurso import Recurso


def seed():
    engine = create_engine(get_database_url())
    with Session(engine) as db:
        items = [
            {"ong_id": 1, "recurso_id": 10, "cantidad_total": 500, "cantidad_disponible": 500},
            {"ong_id": 1, "recurso_id": 12, "cantidad_total": 200, "cantidad_disponible": 200},
            {"ong_id": 3, "recurso_id": 10, "cantidad_total": 100, "cantidad_disponible": 100},
            {"ong_id": 3, "recurso_id": 12, "cantidad_total": 50, "cantidad_disponible": 50},
            {"ong_id": 5, "recurso_id": 20, "cantidad_total": 30, "cantidad_disponible": 30},
        ]
        # Inventario referencia ongs y recursos por FK: se crean si no existen.
        for ong_id in sorted({i["ong_id"] for i in items}):
            if db.get(ONG, ong_id) is None:
                db.add(ONG(id=ong_id, nombre=f"ONG demo {ong_id}", habilitada=True))
        for recurso_id in sorted({i["recurso_id"] for i in items}):
            if db.get(Recurso, recurso_id) is None:
                db.add(Recurso(id=recurso_id, nombre=f"Recurso demo {recurso_id}", unidad_medida="unidad"))
        db.flush()

        for data in items:
            existente = db.scalar(
                select(Inventario).where(
                    Inventario.ong_id == data["ong_id"],
                    Inventario.recurso_id == data["recurso_id"],
                )
            )
            if not existente:
                db.add(Inventario(**data))
                print(f"[+] Creado inventario: ONG {data['ong_id']}, Recurso {data['recurso_id']} (Stock={data['cantidad_total']})")
            else:
                print(f"[-] Ya existe inventario: ONG {data['ong_id']}, Recurso {data['recurso_id']}")
        db.commit()
    print("Seed finalizado exitosamente.")


if __name__ == "__main__":
    seed()
