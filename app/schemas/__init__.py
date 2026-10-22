"""Esquemas Pydantic de la API externa RescueSync.
Reexporta lo necesario para poder hacer ``from app.schemas import ...``.
"""
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserResponse,
)

from app.schemas.health import HealthResponse

from app.schemas.adjudicacion import (
    AdjudicarOfertasRequest,
    AdjudicarOfertasResponse,
    OfertaAdjudicada,
    RecursoAdjudicado,
)
from app.schemas.catalogo import (
    DisponibilidadResponse,
    OngHabilitada,
    OngsHabilitadasResponse,
    RecursoDisponible,
)
from app.schemas.common import Gravedad, TipoDesastre
from app.schemas.errors import (
    ConflictoInventarioDetalle,
    ConflictoInventarioResponse,
    ErrorResponse,
    errores,
)
from app.schemas.liberacion import (
    LiberarRecursosRequest,
    LiberarRecursosResponse,
    RecursoALiberar,
)
from app.schemas.validacion import (
    ClasificacionRecurso,
    NivelRiesgo,
    OfertaEntrada,
    OfertaValidada,
    PerfilCompetencia,
    RecursoEvaluado,
    RecursoOfertado,
    ValidarOfertasRequest,
    ValidarOfertasResponse,
)

__all__ = [
    "LoginRequest",
    "TokenResponse",
    "UserResponse",
    "HealthResponse",
    "AdjudicarOfertasRequest",
    "AdjudicarOfertasResponse",
    "ClasificacionRecurso",
    "ConflictoInventarioDetalle",
    "ConflictoInventarioResponse",
    "DisponibilidadResponse",
    "ErrorResponse",
    "Gravedad",
    "LiberarRecursosRequest",
    "LiberarRecursosResponse",
    "NivelRiesgo",
    "OfertaAdjudicada",
    "OfertaEntrada",
    "OfertaValidada",
    "OngHabilitada",
    "OngsHabilitadasResponse",
    "PerfilCompetencia",
    "RecursoALiberar",
    "RecursoAdjudicado",
    "RecursoDisponible",
    "RecursoEvaluado",
    "RecursoOfertado",
    "TipoDesastre",
    "ValidarOfertasRequest",
    "ValidarOfertasResponse",
    "errores",
]