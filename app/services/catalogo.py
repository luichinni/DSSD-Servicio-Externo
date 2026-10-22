from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Certificacion, Inventario, ONG, Recurso
from app.schemas.catalogo import OngHabilitada, RecursoDisponible
from app.services.ongs import listar_ongs


def consultar_ongs_habilitadas(db: Session, hoy: date) -> list[OngHabilitada]:
    ongs = listar_ongs(db)
    etiquetas = defaultdict(set)
    if ongs:
        consulta = select(Certificacion, Recurso.nombre).join(
            Recurso, Recurso.id == Certificacion.id_recurso
        ).where(
            Certificacion.id_ong.in_([ong.id for ong in ongs]),
            Certificacion.activa.is_(True),
            Certificacion.fecha_vencimiento >= hoy,
        )
        for certificado, nombre in db.execute(consulta):
            etiquetas[certificado.id_ong].add(
                f"{nombre}: {certificado.tipo_desastre}, {certificado.rol_permitido}, "
                f"riesgo {certificado.riesgo_maximo}"
            )
    return [OngHabilitada(
        id_ong=ong.id,
        nombre=ong.nombre,
        habilitada=ong.habilitada,
        certificaciones=sorted(etiquetas[ong.id]),
    ) for ong in ongs]


def consultar_disponibilidad(
    db: Session, recurso_id: int | None = None, id_ong: int | None = None,
) -> list[RecursoDisponible]:
    consulta = select(
        Inventario.ong_id.label("id_ong"),
        Recurso.id.label("id_recurso"),
        Recurso.nombre.label("nombre_recurso"),
        Inventario.cantidad_disponible.label("inventario_actual"),
        (Inventario.cantidad_total - Inventario.cantidad_disponible).label("cantidad_comprometida"),
    ).select_from(Inventario).join(Recurso, Recurso.id == Inventario.recurso_id).join(
        ONG, ONG.id == Inventario.ong_id
    ).where(ONG.habilitada.is_(True))
    if recurso_id is not None:
        consulta = consulta.where(Recurso.id == recurso_id)
    if id_ong is not None:
        consulta = consulta.where(ONG.id == id_ong)
    consulta = consulta.order_by(Inventario.ong_id, Inventario.recurso_id)
    return [RecursoDisponible.model_validate(fila) for fila in db.execute(consulta).mappings()]
