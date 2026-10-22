from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.cli.seed_certificaciones_demo import cargar_demo
from app.models import Certificacion, Inventario, ONG
from app.schemas import DisponibilidadResponse, OngsHabilitadasResponse

ONGS = "/api/v1/ongs/habilitadas"
DISPONIBILIDAD = "/api/v1/recursos/disponibilidad"


@pytest.mark.parametrize("metodo,ruta", [("get", ONGS), ("get", DISPONIBILIDAD), ("post", "/api/v1/ongs")])
def test_catalogo_requiere_jwt(entorno, metodo, ruta):
    client, _, _ = entorno
    assert getattr(client, metodo)(ruta).status_code == 401


def test_catalogos_vacios_respetan_el_contrato(entorno):
    client, _, headers = entorno
    assert client.get(ONGS, headers=headers).json() == {"total": 0, "ongs": []}
    assert client.get(DISPONIBILIDAD, headers=headers).json() == {"total": 0, "recursos": []}


def test_alta_conserva_el_id_local_y_rechaza_duplicados_sin_sobrescribir(entorno):
    client, db, headers = entorno
    datos = {"id_ong": 37, "nombre": "ONG nueva", "descripcion": None}
    respuesta = client.post("/api/v1/ongs", json=datos, headers=headers)
    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "id_ong": 37, "nombre": "ONG nueva", "habilitada": True, "certificaciones": [],
    }
    assert db.get(ONG, 37).descripcion is None
    datos["nombre"] = "No debe sobrescribir"
    assert client.post("/api/v1/ongs", json=datos, headers=headers).status_code == 409
    assert db.get(ONG, 37).nombre == "ONG nueva"


@pytest.mark.parametrize("datos", [
    {"nombre": "Sin ID"}, {"id_ong": 0, "nombre": "ONG"},
    {"id_ong": 8, "nombre": "   "}, {"id_ong": 8, "nombre": "ONG", "extra": True},
])
def test_alta_exige_id_y_datos_validos(entorno, datos):
    client, _, headers = entorno
    assert client.post("/api/v1/ongs", json=datos, headers=headers).status_code == 422


def test_listado_solo_ongs_habilitadas_y_certificados_vigentes(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    respuesta = client.get(ONGS, headers=headers)
    assert respuesta.status_code == 200
    resultado = OngsHabilitadasResponse.model_validate(respuesta.json())
    assert resultado.total == 2
    ongs = {o.id_ong: o for o in resultado.ongs}
    assert len(ongs[3].certificaciones) == 2
    assert len(ongs[4].certificaciones) == 1  # El certificado vencido no se publica.
    db.get(ONG, 4).habilitada = False
    db.commit()
    respuesta = client.get(ONGS, headers=headers).json()
    assert respuesta["total"] == 1
    assert respuesta["ongs"][0]["id_ong"] == 3


def test_disponibilidad_por_ong_recurso_y_compromisos(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    respuesta = client.get(DISPONIBILIDAD, headers=headers)
    assert respuesta.status_code == 200
    resultado = DisponibilidadResponse.model_validate(respuesta.json())
    assert resultado.total == 4
    respuesta = client.get(DISPONIBILIDAD, params={"id_ong": 3, "recurso_id": 10}, headers=headers)
    assert respuesta.json() == {
        "total": 1,
        "recursos": [{
            "id_ong": 3, "id_recurso": 10, "nombre_recurso": "Bote de rescate demo",
            "inventario_actual": 80, "cantidad_comprometida": 20,
        }],
    }
    db.get(ONG, 3).habilitada = False
    db.commit()
    assert client.get(DISPONIBILIDAD, params={"id_ong": 3}, headers=headers).json()["total"] == 0


@pytest.mark.parametrize("parametro", ["recurso_id", "id_ong"])
def test_filtros_rechazan_ids_no_positivos(entorno, parametro):
    client, _, headers = entorno
    assert client.get(DISPONIBILIDAD, params={parametro: 0}, headers=headers).status_code == 422


def test_inventario_no_se_modifica_al_consultar_o_validar(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    antes = [(i.id, i.cantidad_total, i.cantidad_disponible) for i in db.scalars(select(Inventario))]
    for ruta in (ONGS, DISPONIBILIDAD):
        assert client.get(ruta, headers=headers).status_code == 200
    respuesta = client.post("/api/v1/ofertas/validar", headers=headers, json={
        "id_emergencia": 101, "tipo_desastre": "hidrologico", "gravedad": "alto",
        "ofertas": [{"id_oferta": 15, "es_conjunta": False, "id_ong": 3,
                     "recursos": [{"id_recurso": 10, "cantidad_ofrecida": 500}]}],
    })
    assert respuesta.status_code == 200  # Competencias, no reserva ni chequeo de stock.
    assert antes == [(i.id, i.cantidad_total, i.cantidad_disponible) for i in db.scalars(select(Inventario))]


@pytest.mark.parametrize("fallo,ruta", [
    ("consultar_ongs_habilitadas", ONGS), ("consultar_disponibilidad", DISPONIBILIDAD),
])
def test_fallo_de_base_del_catalogo_devuelve_503(entorno, monkeypatch, fallo, ruta):
    client, _, headers = entorno

    def consulta_fallida(*args, **kwargs):
        raise OperationalError("select", {}, Exception("offline"))

    monkeypatch.setattr("app.api.routes.catalogo." + fallo, consulta_fallida)
    assert client.get(ruta, headers=headers).status_code == 503


def test_swagger_publica_catalogo_con_contrato_y_seguridad(entorno):
    client, _, _ = entorno
    esquema = client.get("/openapi.json").json()
    for ruta in (ONGS, DISPONIBILIDAD, "/api/v1/ongs"):
        operacion = esquema["paths"][ruta]["post" if ruta.endswith("/ongs") else "get"]
        assert operacion["security"]
    assert "/catalogo/disponibilidad" not in esquema["paths"]
    assert esquema["paths"][DISPONIBILIDAD]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/DisponibilidadResponse")


def test_referencias_y_cantidades_del_inventario_estan_protegidas(entorno):
    _, db, _ = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    db.add(Inventario(ong_id=999, recurso_id=10, cantidad_total=1, cantidad_disponible=1))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    inventario = db.scalar(select(Inventario).where(Inventario.ong_id == 3, Inventario.recurso_id == 10))
    inventario.cantidad_disponible = inventario.cantidad_total + 1
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    db.add(Certificacion(
        id_ong=999, id_recurso=10, tipo_desastre="hidrologico", rol_permitido="lote_principal",
        riesgo_maximo="alto", perfil_competencia="Avanzado",
        fecha_vencimiento=datetime.now(timezone.utc).date(), activa=True,
    ))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_carga_demo_respeta_ongs_reales_deshabilitadas_y_stock_existente(entorno):
    _, db, _ = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    db.get(ONG, 3).nombre = "Nombre real"
    db.get(ONG, 3).habilitada = False
    inventario = db.scalar(select(Inventario).where(Inventario.ong_id == 3, Inventario.recurso_id == 10))
    inventario.cantidad_disponible = 7
    db.commit()
    assert cargar_demo(db, datetime.now(timezone.utc).date()) == 0
    db.commit()
    assert db.get(ONG, 3).nombre == "Nombre real"
    assert db.get(ONG, 3).habilitada is False
    assert inventario.cantidad_disponible == 7
