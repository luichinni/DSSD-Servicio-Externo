from app.schemas.validacion import NivelRiesgo, PerfilCompetencia

ORDEN_RIESGO = {nivel: orden for orden, nivel in enumerate(NivelRiesgo, start=1)}
ORDEN_PERFIL = {perfil: orden for orden, perfil in enumerate(PerfilCompetencia)}

# La tabla conserva los valores originales; la salida respeta el contrato de Dev 2.
# El contrato no publica riesgo crítico: esos registros se limitan a Alto al evaluar.
RIESGO_PUBLICO = {
    "bajo": NivelRiesgo.BAJO,
    "medio": NivelRiesgo.MEDIO,
    "alto": NivelRiesgo.ALTO,
    "critico": NivelRiesgo.ALTO,
}
