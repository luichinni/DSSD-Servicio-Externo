"""Script temporal para poblar InventarioNacional de prueba."""

import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_database_url
from app.models.inventario_nacional import InventarioNacional


def seed():
    engine = create_engine(get_database_url())
    with Session(engine) as db:
        items = [
            {"id_ong": 1, "id_recurso": 10, "cantidad_total": 500, "cantidad_disponible": 500},
            {"id_ong": 1, "id_recurso": 12, "cantidad_total": 200, "cantidad_disponible": 200},
            {"id_ong": 3, "id_recurso": 10, "cantidad_total": 100, "cantidad_disponible": 100},
            {"id_ong": 3, "id_recurso": 12, "cantidad_total": 50, "cantidad_disponible": 50},
            {"id_ong": 5, "id_recurso": 20, "cantidad_total": 30, "cantidad_disponible": 30},
        ]
        for data in items:
            existente = db.scalar(
                select(InventarioNacional).where(
                    InventarioNacional.id_ong == data["id_ong"],
                    InventarioNacional.id_recurso == data["id_recurso"],
                )
            )
            if not existente:
                db.add(InventarioNacional(**data))
                print(f"[+] Creado inventario: ONG {data['id_ong']}, Recurso {data['id_recurso']} (Stock={data['cantidad_total']})")
            else:
                print(f"[-] Ya existe inventario: ONG {data['id_ong']}, Recurso {data['id_recurso']}")
        db.commit()
    print("Seed finalizado exitosamente.")


if __name__ == "__main__":
    seed()
