from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import ONG, Inventario, Recurso

def consultar_disponibilidad(db: Session) -> list[dict]:
    consulta = (
        select(
            Recurso.id.label("recurso_id"),
            Recurso.nombre.label("nombre"),
            Recurso.unidad_medida.label("unidad_medida"),
            func.coalesce(func.sum(Inventario.cantidad), 0).label("cantidad_disponible"),
        ).outerjoin(Inventario, Recurso.id == Inventario.recurso_id)
        .outerjoin(ONG, Inventario.ong_id == ONG.id)
        .where((ONG.habilitada.is_(True)) | (Inventario.id.is_(None)))
        .group_by(Recurso.id, Recurso.nombre, Recurso.unidad_medida)
        .order_by(Recurso.nombre.asc())
    )

    resultados = db.execute(consulta).mappings().all()
    return [dict(fila) for fila in resultados]