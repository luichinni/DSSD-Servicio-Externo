from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.cli.seed_certificaciones_demo import cargar_catalogo_demo, cargar_demo
from app.core.security import create_access_token
from app.models import Certificacion, User, ONG, Recurso
from app.schemas import ValidarOfertasRequest, ValidarOfertasResponse
from app.services.validacion import CertificacionNoEncontrada, evaluar_ofertas

URL = "/api/v1/ofertas/validar"
HOY = date(2026, 10, 17)


def payload() -> dict:
    return {
        "id_emergencia": 101,
        "tipo_desastre": "hidrologico",
        "gravedad": "alto",
        "ofertas": [{
            "id_oferta": 15, "es_conjunta": False, "id_ong": 3,
            "recursos": [{"id_recurso": 10, "cantidad_ofrecida": 50}],
        }],
    }


def certificado(**cambios) -> Certificacion:
    valores = dict(
        id=1, id_ong=3, id_recurso=10, tipo_desastre="hidrologico",
        rol_permitido="lote_principal", riesgo_maximo="alto",
        perfil_competencia="Avanzado", fecha_vencimiento=HOY, activa=True,
    )
    valores.update(cambios)
    return Certificacion(**valores)


@pytest.mark.parametrize("rol", ["lote_principal", "apoyo_secundario"])
def test_certificado_vigente_incluye_el_dia_de_vencimiento(rol):
    resultado = evaluar_ofertas(
        ValidarOfertasRequest.model_validate(payload()), [certificado(rol_permitido=rol)], HOY
    )
    recurso = resultado.ofertas_validadas[0].recursos_evaluados[0]
    assert resultado.estado_general == "validado"
    assert recurso.clasificacion == rol
    assert recurso.cantidad_validada == 50
    assert resultado.ofertas_validadas[0].nivel_riesgo_permitido == "Alto"


@pytest.mark.parametrize("cambios", [
    {"fecha_vencimiento": HOY - timedelta(days=1)},
    {"activa": False},
    {"tipo_desastre": "incendio_forestal"},
    {"id_ong": 4},
    {"id_recurso": 12},
])
def test_sin_certificacion_vigente_no_inventa_una_habilitacion(cambios):
    with pytest.raises(CertificacionNoEncontrada, match="ONG 3, recurso 10"):
        evaluar_ofertas(
            ValidarOfertasRequest.model_validate(payload()), [certificado(**cambios)], HOY
        )


def test_riesgo_inferior_se_adapta_a_apoyo_con_su_limite():
    resultado = evaluar_ofertas(
        ValidarOfertasRequest.model_validate(payload()),
        [certificado(riesgo_maximo="bajo", perfil_competencia="Basico")], HOY,
    )
    oferta = resultado.ofertas_validadas[0]
    recurso = oferta.recursos_evaluados[0]
    assert recurso.clasificacion == "apoyo_secundario"
    assert oferta.nivel_riesgo_permitido == "Bajo"
    assert recurso.cantidad_validada == 50
    assert "hasta Bajo" in recurso.observacion
    assert "No habilita" in recurso.observacion


def test_no_combina_el_rol_de_un_certificado_con_el_riesgo_de_otro():
    evidencia = [
        certificado(riesgo_maximo="bajo", perfil_competencia="Basico"),
        certificado(id=2, rol_permitido="apoyo_secundario", perfil_competencia="Intermedio"),
    ]
    resultado = evaluar_ofertas(ValidarOfertasRequest.model_validate(payload()), evidencia, HOY)
    oferta = resultado.ofertas_validadas[0]
    assert oferta.recursos_evaluados[0].clasificacion == "apoyo_secundario"
    assert oferta.perfil_competencia_ong == "Intermedio"
    assert oferta.nivel_riesgo_permitido == "Alto"


def test_prioriza_principal_y_resuelve_empates_sin_depender_del_orden():
    evidencia = [
        certificado(id=3, rol_permitido="apoyo_secundario"),
        certificado(id=2), certificado(id=1, perfil_competencia="Basico"),
    ]
    solicitud = ValidarOfertasRequest.model_validate(payload())
    a = evaluar_ofertas(solicitud, evidencia, HOY)
    b = evaluar_ofertas(solicitud, list(reversed(evidencia)), HOY)
    assert a == b
    assert a.ofertas_validadas[0].recursos_evaluados[0].clasificacion == "lote_principal"
    assert a.ofertas_validadas[0].perfil_competencia_ong == "Basico"


def test_gravedad_critica_respeta_el_maximo_riesgo_del_contrato():
    datos = payload()
    datos["gravedad"] = "critico"
    resultado = evaluar_ofertas(
        ValidarOfertasRequest.model_validate(datos), [certificado(riesgo_maximo="critico")], HOY
    )
    oferta = resultado.ofertas_validadas[0]
    assert oferta.nivel_riesgo_permitido == "Alto"
    assert oferta.recursos_evaluados[0].clasificacion == "apoyo_secundario"
    assert "hasta Alto" in oferta.recursos_evaluados[0].observacion


def test_payload_bonita_consulta_bd_y_devuelve_exactamente_el_contrato(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    solicitud = payload()
    solicitud["ofertas"][0]["recursos"].append({"id_recurso": 12, "cantidad_ofrecida": 5})
    antes = [(c.id, c.activa, c.fecha_vencimiento) for c in db.scalars(select(Certificacion))]
    respuesta = client.post(URL, json=solicitud, headers=headers)
    repetida = client.post(URL, json=solicitud, headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.json() == repetida.json()
    cuerpo = respuesta.json()
    ValidarOfertasResponse.model_validate(cuerpo)
    assert cuerpo["id_emergencia"] == 101
    assert cuerpo["estado_general"] == "validado"
    oferta = cuerpo["ofertas_validadas"][0]
    assert (oferta["id_oferta"], oferta["id_ong"]) == (15, 3)
    assert [r["clasificacion"] for r in oferta["recursos_evaluados"]] == [
        "lote_principal", "apoyo_secundario",
    ]
    assert set(oferta["recursos_evaluados"][0]) == {
        "id_recurso", "cantidad_validada", "clasificacion", "observacion",
    }
    assert antes == [(c.id, c.activa, c.fecha_vencimiento) for c in db.scalars(select(Certificacion))]


def test_oferta_conjunta_se_evalua_por_participante_sin_compartir_certificados(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    solicitud = payload()
    solicitud["ofertas"][0]["es_conjunta"] = True
    primera = client.post(URL, json=solicitud, headers=headers)
    assert primera.status_code == 200
    assert primera.json()["ofertas_validadas"][0]["recursos_evaluados"][0]["clasificacion"] == "lote_principal"
    solicitud["ofertas"][0]["id_ong"] = 4
    segunda = client.post(URL, json=solicitud, headers=headers)
    assert segunda.status_code == 404
    assert "ONG 4, recurso 10" in segunda.json()["detail"]
    solicitud["ofertas"][0]["recursos"][0]["id_recurso"] = 12
    tercera = client.post(URL, json=solicitud, headers=headers)
    assert tercera.status_code == 200
    assert tercera.json()["ofertas_validadas"][0]["nivel_riesgo_permitido"] == "Bajo"


def test_referencia_sin_evidencia_devuelve_404_sin_estado_adicional(entorno):
    client, _, headers = entorno
    respuesta = client.post(URL, json=payload(), headers=headers)
    assert respuesta.status_code == 404
    assert set(respuesta.json()) == {"detail"}


@pytest.mark.parametrize("token", [None, "invalid.token", "expired"])
def test_endpoint_exige_jwt_valido(entorno, token):
    client, db, _ = entorno
    if token == "expired":
        token = create_access_token(db.scalar(select(User.id)), timedelta(seconds=-1))
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    assert client.post(URL, json=payload(), headers=headers).status_code == 401


@pytest.mark.parametrize("cantidad", [0, -1, 1.5])
def test_rechaza_cantidades_invalidas_del_contrato(entorno, cantidad):
    client, _, headers = entorno
    solicitud = payload()
    solicitud["ofertas"][0]["recursos"][0]["cantidad_ofrecida"] = cantidad
    assert client.post(URL, json=solicitud, headers=headers).status_code == 422


@pytest.mark.parametrize("caso", ["ofertas_vacias", "recursos_vacios", "duplicado", "oferta_duplicada", "gravedad", "id", "desastre"])
def test_rechaza_payload_fuera_del_contrato(entorno, caso):
    client, _, headers = entorno
    solicitud = payload()
    oferta = solicitud["ofertas"][0]
    if caso == "ofertas_vacias":
        solicitud["ofertas"] = []
    elif caso == "recursos_vacios":
        oferta["recursos"] = []
    elif caso == "duplicado":
        oferta["recursos"] *= 2
    elif caso == "oferta_duplicada":
        otra = dict(oferta, id_ong=4, es_conjunta=True)
        solicitud["ofertas"].append(otra)
    elif caso == "gravedad":
        solicitud["gravedad"] = "alta"
    elif caso == "id":
        oferta["id_ong"] = 0
    else:
        solicitud["tipo_desastre"] = "inundacion"
    assert client.post(URL, json=solicitud, headers=headers).status_code == 422


def test_normalizacion_del_contrato_funciona_con_la_consulta_nacional(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    solicitud = payload()
    solicitud["tipo_desastre"] = " Hidrológico "
    solicitud["gravedad"] = " ALTO "
    assert client.post(URL, json=solicitud, headers=headers).status_code == 200


def test_falla_de_consulta_no_parece_certificacion_ausente(entorno, monkeypatch):
    client, _, headers = entorno

    def consulta_fallida(*args):
        raise OperationalError("select", {}, Exception("connection lost"))

    monkeypatch.setattr("app.api.routes.ofertas.consultar_certificaciones", consulta_fallida)
    respuesta = client.post(URL, json=payload(), headers=headers)
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detail": "Database unavailable"}


def test_swagger_documenta_el_contrato_y_jwt_sin_duplicar_rutas(entorno):
    client, _, _ = entorno
    esquema = client.get("/openapi.json").json()
    operacion = esquema["paths"][URL]["post"]
    assert operacion["security"]
    assert {"200", "401", "404", "422", "503"} <= set(operacion["responses"])
    assert operacion["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/ValidarOfertasRequest")
    assert all("/api/v1/api/v1" not in path for path in esquema["paths"])


def test_carga_demo_se_puede_repetir_sin_sobrescribir(entorno):
    _, db, _ = entorno
    assert cargar_demo(db, HOY) == 4
    db.commit()
    primero = db.scalar(select(Certificacion).order_by(Certificacion.id))
    primero.activa = False
    db.commit()
    assert cargar_demo(db, HOY + timedelta(days=1)) == 0
    assert db.scalar(select(func.count()).select_from(Certificacion)) == 4
    assert primero.activa is False


def test_demo_nuevo_preserva_certificaciones_anteriores(entorno):
    _, db, _ = entorno
    cargar_catalogo_demo(db)
    anterior = certificado(id=None, tipo_desastre="inundacion")
    db.add(anterior)
    db.commit()
    assert cargar_demo(db, HOY) == 4
    db.commit()
    assert db.scalar(select(func.count()).select_from(Certificacion)) == 5
    assert anterior.tipo_desastre == "inundacion"


def test_ong_inhabilitada_no_se_valida_aunque_tenga_certificado_vigente(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    db.get(ONG, 3).habilitada = False
    db.commit()
    respuesta = client.post(URL, json=payload(), headers=headers)
    assert respuesta.status_code == 404
    assert "no está habilitada" in respuesta.json()["detail"]


def test_recurso_inexistente_se_detecta_en_el_catalogo(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.commit()
    solicitud = payload()
    solicitud["ofertas"][0]["recursos"][0]["id_recurso"] = 99
    respuesta = client.post(URL, json=solicitud, headers=headers)
    assert respuesta.status_code == 404
    assert "[99]" in respuesta.json()["detail"]


def test_recurso_existente_sin_certificado_no_se_confunde_con_recurso_desconocido(entorno):
    client, db, headers = entorno
    cargar_demo(db, datetime.now(timezone.utc).date())
    db.add(Recurso(id=99, nombre="Otro recurso", unidad_medida="unidad"))
    db.commit()
    solicitud = payload()
    solicitud["ofertas"][0]["recursos"][0]["id_recurso"] = 99
    respuesta = client.post(URL, json=solicitud, headers=headers)
    assert respuesta.status_code == 404
    assert "certificación vigente" in respuesta.json()["detail"]
