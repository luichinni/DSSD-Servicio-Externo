import copy

import pytest
from pydantic import ValidationError

from app.schemas import (
    AdjudicarOfertasRequest,
    AdjudicarOfertasResponse,
    LiberarRecursosRequest,
    LiberarRecursosResponse,
    ValidarOfertasRequest,
    ValidarOfertasResponse,
)

"""Verifica que los JSON de la especificación pasen por los esquemas y que las validaciones rechacen lo que corresponde."""

MODELOS = [
    ValidarOfertasRequest,
    ValidarOfertasResponse,
    AdjudicarOfertasRequest,
    AdjudicarOfertasResponse,
    LiberarRecursosRequest,
    LiberarRecursosResponse,
]


def _ejemplo(modelo):
    return copy.deepcopy(modelo.model_config["json_schema_extra"]["examples"][0])


@pytest.mark.parametrize("modelo", MODELOS)
def test_ejemplo_swagger_es_valido(modelo):
    """El ejemplo que se ve en /docs debe poder parsearse con su propio esquema."""
    modelo.model_validate(_ejemplo(modelo))


def test_campo_extra_es_rechazado():
    data = _ejemplo(ValidarOfertasRequest)
    data["campo_inventado"] = 1
    with pytest.raises(ValidationError):
        ValidarOfertasRequest.model_validate(data)


def test_cantidad_cero_es_rechazada():
    data = _ejemplo(AdjudicarOfertasRequest)
    data["ofertas_adjudicadas"][0]["recursos"][0]["cantidad_adjudicada"] = 0
    with pytest.raises(ValidationError):
        AdjudicarOfertasRequest.model_validate(data)


def test_ofertas_vacias_son_rechazadas():
    data = _ejemplo(ValidarOfertasRequest)
    data["ofertas"] = []
    with pytest.raises(ValidationError):
        ValidarOfertasRequest.model_validate(data)


def test_recursos_duplicados_son_rechazados():
    data = _ejemplo(LiberarRecursosRequest)
    data["recursos_a_liberar"].append({"id_recurso": 10, "cantidad_liberada": 1})
    with pytest.raises(ValidationError):
        LiberarRecursosRequest.model_validate(data)


def test_ofertas_duplicadas_son_rechazadas():
    data = _ejemplo(ValidarOfertasRequest)
    data["ofertas"].append(copy.deepcopy(data["ofertas"][0]))
    with pytest.raises(ValidationError):
        ValidarOfertasRequest.model_validate(data)


def test_timestamp_se_serializa_en_utc_con_z():
    resp = AdjudicarOfertasResponse.model_validate(_ejemplo(AdjudicarOfertasResponse))
    assert resp.model_dump_json().count("2026-10-12T15:30:00Z") == 1


def test_timestamp_sin_zona_horaria_es_rechazado():
    data = _ejemplo(AdjudicarOfertasResponse)
    data["timestamp_bloqueo"] = "2026-10-12T15:30:00"
    with pytest.raises(ValidationError):
        AdjudicarOfertasResponse.model_validate(data)


# --- tipo_desastre / gravedad ------------------------------------------------
from app.schemas import Gravedad, TipoDesastre  # noqa: E402


def test_tipo_desastre_invalido_es_rechazado():
    data = _ejemplo(ValidarOfertasRequest)
    data["tipo_desastre"] = "saraza"
    with pytest.raises(ValidationError):
        ValidarOfertasRequest.model_validate(data)


@pytest.mark.parametrize("valor", ["hidrologico", "Hidrológico", " HIDROLOGICO "])
def test_tipo_desastre_tolera_mayusculas_y_tildes(valor):
    data = _ejemplo(ValidarOfertasRequest)
    data["tipo_desastre"] = valor
    assert ValidarOfertasRequest.model_validate(data).tipo_desastre is TipoDesastre.HIDROLOGICO


def test_tipo_desastre_con_espacio():
    data = _ejemplo(ValidarOfertasRequest)
    data["tipo_desastre"] = "Incendio Forestal"
    assert ValidarOfertasRequest.model_validate(data).tipo_desastre is TipoDesastre.INCENDIO_FORESTAL


@pytest.mark.parametrize("valor", ["saraza", 3, "alta"])
def test_gravedad_invalida_es_rechazada(valor):
    data = _ejemplo(ValidarOfertasRequest)
    data["gravedad"] = valor
    with pytest.raises(ValidationError):
        ValidarOfertasRequest.model_validate(data)


def test_gravedad_mapea_a_nivel_numerico():
    assert [g.nivel for g in Gravedad] == [1, 2, 3, 4]