from collections import defaultdict
from datetime import date
from typing import Sequence

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.core.competencias import ORDEN_PERFIL, ORDEN_RIESGO, RIESGO_PUBLICO
from app.models.certificacion import Certificacion
from app.models import ONG, Recurso
from app.schemas.validacion import (
    ClasificacionRecurso,
    OfertaValidada,
    PerfilCompetencia,
    RecursoEvaluado,
    ValidarOfertasRequest,
    ValidarOfertasResponse,
)


class CertificacionNoEncontrada(ValueError):
    """Falta evidencia nacional vigente para evaluar un aporte."""


class ReferenciaNoDisponible(ValueError):
    """El aporte referencia una entidad inexistente o una ONG no habilitada."""


def consultar_certificaciones(db: Session, datos: ValidarOfertasRequest) -> list[Certificacion]:
    ids_ongs = {oferta.id_ong for oferta in datos.ofertas}
    ongs = {ong.id: ong for ong in db.scalars(select(ONG).where(ONG.id.in_(ids_ongs)))}
    for id_ong in sorted(ids_ongs):
        if id_ong not in ongs:
            raise ReferenciaNoDisponible(f"La ONG {id_ong} no existe en el catálogo nacional.")
        if not ongs[id_ong].habilitada:
            raise ReferenciaNoDisponible(f"La ONG {id_ong} no está habilitada.")
    ids_recursos = {r.id_recurso for oferta in datos.ofertas for r in oferta.recursos}
    existentes = set(db.scalars(select(Recurso.id).where(Recurso.id.in_(ids_recursos))))
    faltantes = sorted(ids_recursos - existentes)
    if faltantes:
        raise ReferenciaNoDisponible(f"Recursos inexistentes en el catálogo nacional: {faltantes}.")
    claves = {
        (oferta.id_ong, recurso.id_recurso)
        for oferta in datos.ofertas
        for recurso in oferta.recursos
    }
    consulta = select(Certificacion).where(
        tuple_(Certificacion.id_ong, Certificacion.id_recurso).in_(claves)
    )
    return list(db.scalars(consulta).all())


def evaluar_ofertas(
    datos: ValidarOfertasRequest,
    certificaciones: Sequence[Certificacion],
    fecha_evaluacion: date,
) -> ValidarOfertasResponse:
    """Evalúa evidencia ya cargada sin consultar ni modificar la base de datos."""
    evidencia = defaultdict(list)
    for certificado in certificaciones:
        evidencia[(certificado.id_ong, certificado.id_recurso)].append(certificado)

    ofertas = []
    for oferta in datos.ofertas:
        resultados = []
        seleccionadas = []
        for recurso in oferta.recursos:
            vigentes = [
                certificado
                for certificado in evidencia[(oferta.id_ong, recurso.id_recurso)]
                if certificado.tipo_desastre == datos.tipo_desastre
                and certificado.activa
                and certificado.fecha_vencimiento >= fecha_evaluacion
            ]
            if not vigentes:
                raise CertificacionNoEncontrada(
                    "No se encontró certificación vigente aplicable para "
                    f"la ONG {oferta.id_ong}, recurso {recurso.id_recurso} "
                    f"y desastre {datos.tipo_desastre.value}."
                )

            def puede_ser_principal(certificado: Certificacion) -> bool:
                return (
                    certificado.rol_permitido == ClasificacionRecurso.LOTE_PRINCIPAL
                    and ORDEN_RIESGO[RIESGO_PUBLICO[certificado.riesgo_maximo]] >= datos.gravedad.nivel
                )

            # Elegir una certificación completa, sin combinar permisos entre registros.
            vigentes.sort(key=lambda c: (
                not puede_ser_principal(c),
                -ORDEN_RIESGO[RIESGO_PUBLICO[c.riesgo_maximo]],
                c.id,
            ))
            certificado = vigentes[0]
            riesgo = RIESGO_PUBLICO[certificado.riesgo_maximo]
            if puede_ser_principal(certificado):
                clasificacion = ClasificacionRecurso.LOTE_PRINCIPAL
                observacion = "Habilitación vigente para actuar como responsable principal."
            else:
                clasificacion = ClasificacionRecurso.APOYO_SECUNDARIO
                observacion = (
                    f"Apoyo bajo supervisión, únicamente en tareas de riesgo hasta {riesgo.value}. "
                    "No habilita tareas que superen ese nivel."
                )
            resultados.append(RecursoEvaluado(
                id_recurso=recurso.id_recurso,
                cantidad_validada=recurso.cantidad_ofrecida,
                clasificacion=clasificacion,
                observacion=observacion,
            ))
            seleccionadas.append(certificado)

        ofertas.append(OfertaValidada(
            id_oferta=oferta.id_oferta,
            id_ong=oferta.id_ong,
            perfil_competencia_ong=max(
                (PerfilCompetencia(c.perfil_competencia) for c in seleccionadas),
                key=ORDEN_PERFIL.__getitem__,
            ),
            nivel_riesgo_permitido=max(
                (RIESGO_PUBLICO[c.riesgo_maximo] for c in seleccionadas),
                key=ORDEN_RIESGO.__getitem__,
            ),
            recursos_evaluados=resultados,
        ))

    return ValidarOfertasResponse(
        id_emergencia=datos.id_emergencia,
        estado_general="validado",
        ofertas_validadas=ofertas,
    )
