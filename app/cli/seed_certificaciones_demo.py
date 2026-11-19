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


def cargar_catalogo_integracion(db: Session, hoy: date) -> int:
    """Alinea ONGs, recursos, inventarios y certificaciones con los IDs base de DSSD-FlaskApp."""
    ongs_flask = [
        (1, "Red de Apoyo Comunitario", "ONG base de DSSD-FlaskApp."),
        (2, "Brigada Humanitaria Federal", "ONG colaboradora base de DSSD-FlaskApp."),
        (3, "Cruz Verde Solidaria", "ONG de respuesta rápida y logística."),
    ]
    for id_ong, nombre, desc in ongs_flask:
        ong = db.get(ONG, id_ong)
        if ong is None:
            db.add(ONG(id=id_ong, nombre=nombre, descripcion=desc, habilitada=True))
        else:
            ong.habilitada = True

    recursos_flask = [
        (1, "Paramédicos de Emergencia", "persona"),
        (2, "Raciones de Alimento Seco", "racion"),
        (3, "Ambulancia de Traslado 4x4", "unidad"),
        (4, "Carpas Sanitarias de Campaña", "unidad"),
        (5, "Kits de Higiene Comunitarios", "kit"),
    ]
    for id_recurso, nombre, unidad in recursos_flask:
        recurso = db.get(Recurso, id_recurso)
        if recurso is None:
            db.add(Recurso(id=id_recurso, nombre=nombre, unidad_medida=unidad))
    db.flush()

    for id_ong, _, _ in ongs_flask:
        for id_recurso, _, _ in recursos_flask:
            inv = db.scalar(select(Inventario).where(
                Inventario.ong_id == id_ong,
                Inventario.recurso_id == id_recurso,
            ))
            if inv is None:
                db.add(Inventario(
                    ong_id=id_ong,
                    recurso_id=id_recurso,
                    cantidad_total=10000,
                    cantidad_disponible=10000,
                ))
            elif inv.cantidad_disponible < 5000:
                delta = 10000 - inv.cantidad_disponible
                inv.cantidad_total = max(inv.cantidad_total + delta, 10000)
                inv.cantidad_disponible = 10000
    db.flush()

    tipos_desastre = ("geologico", "meteorologico", "hidrologico", "biologico", "incendio_forestal")
    creadas = 0
    for id_ong, _, _ in ongs_flask:
        for id_recurso, _, _ in recursos_flask:
            for tipo in tipos_desastre:
                cert = db.scalar(select(Certificacion).where(
                    Certificacion.id_ong == id_ong,
                    Certificacion.id_recurso == id_recurso,
                    Certificacion.tipo_desastre == tipo,
                    Certificacion.rol_permitido == "lote_principal",
                ))
                if cert is None:
                    db.add(Certificacion(
                        id_ong=id_ong,
                        id_recurso=id_recurso,
                        tipo_desastre=tipo,
                        rol_permitido="lote_principal",
                        riesgo_maximo="critico",
                        perfil_competencia="Avanzado",
                        fecha_vencimiento=hoy + timedelta(days=365),
                        activa=True,
                    ))
                    creadas += 1
                else:
                    cert.activa = True
                    cert.riesgo_maximo = "critico"
                    if cert.fecha_vencimiento < hoy + timedelta(days=30):
                        cert.fecha_vencimiento = hoy + timedelta(days=365)
    return creadas


def main() -> None:
    hoy = ahora_ar().date()
    with get_session_factory()() as db, db.begin():
        creadas = cargar_demo(db, hoy)
        integracion = cargar_catalogo_integracion(db, hoy)
    print(f"Certificaciones ficticias creadas: {creadas}. Integración Flask: {integracion}. Usar solo en desarrollo.")


if __name__ == "__main__":
    main()
