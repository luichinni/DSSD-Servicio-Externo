from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compromiso_recurso import CompromisoRecurso, EstadoCompromiso
from app.models.inventario_nacional import InventarioNacional
from app.schemas.adjudicacion import (
    AdjudicarRequest,
    AdjudicarResponse,
    OfertaAdjudicadaResultado,
    OfertaRechazadaDetalle,
    RecursoSinStockDetalle,
)


def procesar_adjudicacion(
    db: Session,
    request: AdjudicarRequest,
) -> tuple[AdjudicarResponse, int]:
    ahora = datetime.now(timezone.utc)

    # Recolectar todas las parejas (id_ong, id_recurso) para pre-bloquear con with_for_update() en orden determinista
    pares_a_bloquear = sorted(
        {
            (item.id_ong, rec.id_recurso)
            for item in request.ofertas_adjudicadas
            for rec in item.recursos
        }
    )

    inventarios_por_par: dict[tuple[int, int], InventarioNacional] = {}
    for ong_id, rec_id in pares_a_bloquear:
        query = (
            select(InventarioNacional)
            .where(
                InventarioNacional.id_ong == ong_id,
                InventarioNacional.id_recurso == rec_id,
            )
            .with_for_update()
        )
        inv = db.scalar(query)
        if inv is not None:
            inventarios_por_par[(ong_id, rec_id)] = inv

    ofertas_adjudicadas_resp: list[OfertaAdjudicadaResultado] = []
    ofertas_rechazadas_resp: list[OfertaRechazadaDetalle] = []

    for item in request.ofertas_adjudicadas:
        recursos_rechazados: list[RecursoSinStockDetalle] = []
        recursos_a_descontar: list[tuple[InventarioNacional, int]] = []
        nuevos_compromisos: list[CompromisoRecurso] = []

        for rec in item.recursos:
            par = (item.id_ong, rec.id_recurso)
            inv = inventarios_por_par.get(par)

            # Verificar si ya existe un compromiso registrado previamente
            compromiso_existente = db.scalar(
                select(CompromisoRecurso).where(
                    CompromisoRecurso.id_emergencia == request.id_emergencia,
                    CompromisoRecurso.id_oferta == item.id_oferta,
                    CompromisoRecurso.id_ong == item.id_ong,
                    CompromisoRecurso.id_recurso == rec.id_recurso,
                )
            )

            if compromiso_existente is not None:
                if compromiso_existente.estado == EstadoCompromiso.LIBERADO:
                    recursos_rechazados.append(
                        RecursoSinStockDetalle(
                            id_recurso=rec.id_recurso,
                            cantidad_solicitada=rec.cantidad_adjudicada,
                            cantidad_disponible=inv.cantidad_disponible if inv else 0,
                            motivo="ya_liberado",
                        )
                    )
                elif compromiso_existente.cantidad_comprometida != rec.cantidad_adjudicada:
                    recursos_rechazados.append(
                        RecursoSinStockDetalle(
                            id_recurso=rec.id_recurso,
                            cantidad_solicitada=rec.cantidad_adjudicada,
                            cantidad_disponible=inv.cantidad_disponible if inv else 0,
                            motivo="conflicto_cantidad",
                        )
                    )
                else:
                    # Idempotente: ya está comprometido con la misma cantidad y estado COMPROMETIDO
                    continue
            else:
                if inv is None:
                    recursos_rechazados.append(
                        RecursoSinStockDetalle(
                            id_recurso=rec.id_recurso,
                            cantidad_solicitada=rec.cantidad_adjudicada,
                            cantidad_disponible=0,
                            motivo="inventario_inexistente",
                        )
                    )
                elif inv.cantidad_disponible < rec.cantidad_adjudicada:
                    recursos_rechazados.append(
                        RecursoSinStockDetalle(
                            id_recurso=rec.id_recurso,
                            cantidad_solicitada=rec.cantidad_adjudicada,
                            cantidad_disponible=inv.cantidad_disponible,
                            motivo="stock_insuficiente",
                        )
                    )
                else:
                    # Stock suficiente y válido
                    recursos_a_descontar.append((inv, rec.cantidad_adjudicada))
                    nuevos_compromisos.append(
                        CompromisoRecurso(
                            id_emergencia=request.id_emergencia,
                            id_oferta=item.id_oferta,
                            id_ong=item.id_ong,
                            id_recurso=rec.id_recurso,
                            cantidad_comprometida=rec.cantidad_adjudicada,
                            estado=EstadoCompromiso.COMPROMETIDO,
                            fecha_bloqueo=ahora,
                        )
                    )

        # Regla: aceptación a nivel de oferta. Si un recurso de la oferta falla, toda la oferta se rechaza
        if recursos_rechazados:
            ofertas_rechazadas_resp.append(
                OfertaRechazadaDetalle(
                    id_oferta=item.id_oferta,
                    id_ong=item.id_ong,
                    motivo="No fue posible adjudicar todos los recursos de la oferta",
                    recursos_sin_stock=recursos_rechazados,
                )
            )
        else:
            # Aplicar descuentos e insertar compromisos
            for inv_item, cant in recursos_a_descontar:
                inv_item.cantidad_disponible -= cant
            for comp in nuevos_compromisos:
                db.add(comp)
            ofertas_adjudicadas_resp.append(
                OfertaAdjudicadaResultado(
                    id_oferta=item.id_oferta,
                    id_ong=item.id_ong,
                    estado="adjudicada",
                )
            )

    # Evaluar resultado global
    if not ofertas_adjudicadas_resp:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "id_emergencia": request.id_emergencia,
                "estado": "bloqueo_fallido",
                "mensaje": "Ninguna oferta pudo ser adjudicada por falta de stock o inconsistencias.",
                "ofertas_rechazadas": [o.model_dump() for o in ofertas_rechazadas_resp],
            },
        )

    db.commit()

    estado_global = (
        "bloqueo_exitoso" if not ofertas_rechazadas_resp else "bloqueo_parcial"
    )
    mensaje_global = (
        "Los recursos han sido comprometidos transaccionalmente a nivel nacional."
        if estado_global == "bloqueo_exitoso"
        else "Se adjudicaron parcialmente las ofertas con disponibilidad suficiente."
    )

    respuesta = AdjudicarResponse(
        id_emergencia=request.id_emergencia,
        estado=estado_global,
        mensaje=mensaje_global,
        timestamp_bloqueo=ahora,
        ofertas_adjudicadas=ofertas_adjudicadas_resp,
        ofertas_rechazadas=ofertas_rechazadas_resp,
    )
    return respuesta, status.HTTP_200_OK
