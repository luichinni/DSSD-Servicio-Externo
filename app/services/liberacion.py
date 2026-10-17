from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compromiso_recurso import CompromisoRecurso, EstadoCompromiso
from app.models.inventario_nacional import InventarioNacional
from app.schemas.liberacion import LiberarRequest, LiberarResponse


def procesar_liberacion(
    db: Session,
    request: LiberarRequest,
) -> LiberarResponse:
    ahora = datetime.now(timezone.utc)

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
    inventarios_por_recurso: dict[int, InventarioNacional] = {}

    for rec_id in recursos_unicos:
        inv = db.scalar(
            select(InventarioNacional)
            .where(
                InventarioNacional.id_ong == request.id_ong,
                InventarioNacional.id_recurso == rec_id,
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

    return LiberarResponse(
        estado="liberacion_exitosa",
        id_ong=request.id_ong,
        mensaje="Recursos liberados. Disponibilidad global actualizada.",
        total_recursos_liberados=total_liberados,
    )
