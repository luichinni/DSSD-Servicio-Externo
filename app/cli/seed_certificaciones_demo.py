"""Carga explícita de datos ficticios para una base de desarrollo."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models import Certificacion, Inventario, ONG, Recurso, User
from app.core.timezone import ahora_ar

REFERENCIA_PENDIENTE = "Referencia heredada de certificaciones; completar y verificar antes de habilitar."


def cargar_usuario_demo(db: Session) -> None:
    """Crea el usuario operador por defecto para pruebas si no existe."""
    email_demo = "operador@emergencias.gob.ar"
    if db.scalar(select(User.id).where(User.email == email_demo)) is None:
        db.add(User(email=email_demo, hashed_password=hash_password("PasswordSegura123!")))
        db.flush()


def cargar_catalogo_demo(db: Session) -> None:
    """Carga explícita de ejemplos. Solo completa los placeholders de la migración."""
    for id_ong in (3, 4):
        ong = db.get(ONG, id_ong)
        if ong is None:
            db.add(ONG(
                id=id_ong, nombre=f"ONG Demo {id_ong}",
                descripcion="Datos ficticios para desarrollo.", habilitada=True,
            ))
        elif ong.nombre == f"ONG pendiente #{id_ong}" and ong.descripcion == REFERENCIA_PENDIENTE:
            ong.nombre = f"ONG Demo {id_ong}"
            ong.descripcion = "Datos ficticios para desarrollo."
            ong.habilitada = True

    # ONG 5: Inhabilitada para probar filtros de catálogo y rechazo en validación
    ong_5 = db.get(ONG, 5)
    if ong_5 is None:
        db.add(ONG(
            id=5, nombre="ONG Demo Inhabilitada 5",
            descripcion="ONG suspendida para pruebas de filtro y validación.", habilitada=False,
        ))

    for id_recurso, nombre, unidad in (
        (10, "Bote de rescate demo", "unidad"),
        (12, "Personal de apoyo demo", "persona"),
        (20, "Generador eléctrico demo", "unidad"),
    ):
        recurso = db.get(Recurso, id_recurso)
        if recurso is None:
            db.add(Recurso(id=id_recurso, nombre=nombre, unidad_medida=unidad))
        elif recurso.nombre == f"Recurso pendiente #{id_recurso}":
            recurso.nombre = nombre
            recurso.unidad_medida = unidad
    db.flush()
    for ong_id, recurso_id, total, disponible in (
        (3, 10, 100, 80), (3, 12, 10, 10), (4, 10, 20, 15), (4, 12, 10, 5),
    ):
        existente = db.scalar(select(Inventario.id).where(
            Inventario.ong_id == ong_id, Inventario.recurso_id == recurso_id,
        ))
        if existente is None:
            db.add(Inventario(
                ong_id=ong_id, recurso_id=recurso_id,
                cantidad_total=total, cantidad_disponible=disponible,
            ))
    db.flush()


def cargar_demo(db: Session, hoy: date) -> int:
    cargar_usuario_demo(db)
    cargar_catalogo_demo(db)
    ejemplos = [
        (3, 10, "lote_principal", "alto", "Avanzado", hoy + timedelta(days=365)),
        (3, 12, "apoyo_secundario", "alto", "Intermedio", hoy + timedelta(days=365)),
        (4, 10, "lote_principal", "alto", "Avanzado", hoy - timedelta(days=1)),
        (4, 12, "apoyo_secundario", "bajo", "Basico", hoy + timedelta(days=365)),
    ]
    creadas = 0
    for ong, recurso, rol, riesgo, perfil, vencimiento in ejemplos:
        existente = db.scalar(select(Certificacion.id).where(
            Certificacion.id_ong == ong,
            Certificacion.id_recurso == recurso,
            Certificacion.tipo_desastre == "hidrologico",
            Certificacion.rol_permitido == rol,
        ))
        if existente is not None:
            continue
        db.add(Certificacion(
            id_ong=ong,
            id_recurso=recurso,
            tipo_desastre="hidrologico",
            rol_permitido=rol,
            riesgo_maximo=riesgo,
            perfil_competencia=perfil,
            fecha_vencimiento=vencimiento,
            activa=True,
        ))
        creadas += 1
    return creadas


def main() -> None:
    with get_session_factory()() as db, db.begin():
        creadas = cargar_demo(db, ahora_ar().date())
    print(f"Certificaciones ficticias creadas: {creadas}. Usar solo en desarrollo.")


if __name__ == "__main__":
    main()
