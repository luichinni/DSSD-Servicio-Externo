from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compromiso_recurso import CompromisoRecurso, EstadoCompromiso
from app.models.inventario import Inventario
from app.schemas.liberacion import LiberarRecursosRequest, LiberarRecursosResponse
from app.core.timezone import ahora_ar


def procesar_liberacion(
    db: Session,
    request: LiberarRecursosRequest,
) -> LiberarRecursosResponse:
    ahora = ahora_ar()

    # 1. Buscar todos los compromisos activos para la ONG y emergencia dada
    compromisos_activos = list(
        db.scalars(
            select(CompromisoRecurso).where(
                CompromisoRecurso.id_emergencia == request.id_emergencia,
                CompromisoRecurso.id_ong == request.id_ong,
                CompromisoRecurso.estado == EstadoCompromiso.COMPROMETIDO,
            )
        ).all()
    )

    if not compromisos_activos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No se encontraron recursos comprometidos activos para la "
                f"emergencia {request.id_emergencia} y ONG {request.id_ong}."
            ),
        )

    # 2. Pre-bloquear las filas de inventario involucradas en orden determinista
    recursos_unicos = sorted({comp.id_recurso for comp in compromisos_activos})
    inventarios_por_recurso: dict[int, Inventario] = {}

    for rec_id in recursos_unicos:
        inv = db.scalar(
            select(Inventario)
            .where(
                Inventario.ong_id == request.id_ong,
                Inventario.recurso_id == rec_id,
            )
            .with_for_update()
        )
        if inv is not None:
            inventarios_por_recurso[rec_id] = inv

    total_liberados = 0
    # 3. Restaurar stock disponible y marcar compromisos como LIBERADO
    for comp in compromisos_activos:
        inv = inventarios_por_recurso.get(comp.id_recurso)
        if inv is not None:
            inv.cantidad_disponible = min(
                inv.cantidad_total,
                inv.cantidad_disponible + comp.cantidad_comprometida,
            )
        comp.estado = EstadoCompromiso.LIBERADO
        comp.fecha_liberacion = ahora
        total_liberados += comp.cantidad_comprometida

    db.commit()

    return LiberarRecursosResponse(
        estado="liberacion_exitosa",
        id_ong=request.id_ong,
        mensaje="Recursos liberados. Disponibilidad global actualizada.",
        total_recursos_liberados=total_liberados,
    )
