import concurrent.futures
import os
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.compromiso_recurso import CompromisoRecurso, EstadoCompromiso
from app.models.inventario import Inventario
from app.models.ong import ONG
from app.models.recurso import Recurso
from app.schemas.adjudicacion import AdjudicarOfertasRequest, OfertaAdjudicada, RecursoAdjudicado
from app.services.adjudicacion import procesar_adjudicacion


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL", "").startswith("postgresql"),
    reason="La prueba de locking with_for_update requiere PostgreSQL real",
)
def test_concurrencia_locking_with_for_update_postgres():
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, pool_size=10, max_overflow=5)
    SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)

    # Inicializar un recurso con stock = 100
    with SessionLocal() as db:
        # Limpiar compromisos previos de prueba
        db.query(CompromisoRecurso).filter_by(id_emergencia=9999).delete()
        db.merge(ONG(id=99, nombre="ONG concurrencia test", habilitada=True))
        db.merge(Recurso(id=50, nombre="Recurso concurrencia test", unidad_medida="unidad"))
        db.flush()
        inv = db.scalar(
            select(Inventario).where(
                Inventario.ong_id == 99,
                Inventario.recurso_id == 50,
            )
        )
        if inv is None:
            inv = Inventario(
                ong_id=99,
                recurso_id=50,
                cantidad_total=100,
                cantidad_disponible=100,
            )
            db.add(inv)
        else:
            inv.cantidad_total = 100
            inv.cantidad_disponible = 100
        db.commit()

    # Lanzamos 5 solicitudes concurrentes que intentan adjudicar 30 unidades cada una.
    # Stock = 100. Solo 3 solicitudes deben tener ÃƒÂ©xito (3 x 30 = 90). Las otras 2 deben fallar por falta de stock.
    def intentar_adjudicar(oferta_id: int):
        with SessionLocal() as db:
            req = AdjudicarOfertasRequest(
                id_emergencia=9999,
                ofertas_adjudicadas=[
                    OfertaAdjudicada(
                        id_oferta=oferta_id,
                        id_ong=99,
                        recursos=[RecursoAdjudicado(id_recurso=50, cantidad_adjudicada=30)],
                    )
                ],
            )
            try:
                resp, status_code = procesar_adjudicacion(db=db, request=req)
                return {"status": status_code, "resp": resp}
            except Exception as e:
                return {"status": 409, "error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futuros = [executor.submit(intentar_adjudicar, oferta_id) for oferta_id in range(1, 6)]
        resultados = [f.result() for f in futuros]

    exitos = [r for r in resultados if r.get("status") == 200]
    conflictos = [r for r in resultados if r.get("status") == 409]

    assert len(exitos) == 3
    assert len(conflictos) == 2

    # Verificar consistencia en BD
    with SessionLocal() as db:
        inv_final = db.scalar(
            select(Inventario).where(
                Inventario.ong_id == 99,
                Inventario.recurso_id == 50,
            )
        )
        assert inv_final.cantidad_disponible == 10  # 100 - (3 * 30) = 10

        comps = list(
            db.scalars(
                select(CompromisoRecurso).where(
                    CompromisoRecurso.id_emergencia == 9999,
                    CompromisoRecurso.id_ong == 99,
                    CompromisoRecurso.estado == EstadoCompromiso.COMPROMETIDO,
                )
            ).all()
        )
        assert len(comps) == 3
        # Limpiar
        for c in comps:
            db.delete(c)
        db.delete(inv_final)
        db.commit()

    engine.dispose()
