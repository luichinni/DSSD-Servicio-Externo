"""Metadatos de la documentación OpenAPI/Swagger (/docs).
Observación: Los routers deben usar las constantes TAG_* para que Swagger agrupe bien los
endpoints y no aparezcan grupos duplicados por diferencias de escritura:
    router = APIRouter(prefix="/ofertas", tags=[TAG_OFERTAS])
"""

# --- Tags (usarlos en los routers) -------------------------------------------
TAG_HEALTH = "Health"
TAG_AUTH = "Auth"
TAG_CATALOGO = "Catálogo"
TAG_OFERTAS = "Ofertas"
TAG_PROYECTOS = "Proyectos"

TAGS_METADATA = [
    {
        "name": TAG_HEALTH,
        "description": "Estado del servicio y de la conexión a PostgreSQL.",
    },
    {
        "name": TAG_AUTH,
        "description": "Login y generación del token JWT.",
    },
    {
        "name": TAG_CATALOGO,
        "description": "Consulta de ONGs habilitadas y disponibilidad global de recursos.",
    },
    {
        "name": TAG_OFERTAS,
        "description": "Validación por competencias y adjudicación (bloqueo transaccional) de ofertas.",
    },
    {
        "name": TAG_PROYECTOS,
        "description": "Cierre de proyecto y liberación de recursos comprometidos.",
    },
]

# --- Metadatos generales -------------------------------------------------------
API_TITLE = "RescueSync - API Externa del Sistema Nacional"
API_SUMMARY = "Validación, bloqueo concurrente y liberación de recursos de ONGs."
API_VERSION = "1.0.0"  # misma versión que tenía main.py; ajustar si el equipo versiona distinto

API_DESCRIPTION = """
API consumida por **Bonita BPM** y por el Municipio para coordinar recursos de ONGs
durante una emergencia. Los datos se persisten en PostgreSQL.

## Flujo principal

1. `POST /api/v1/ofertas/validar`: evalúa cada oferta según las certificaciones de la ONG
   y asigna perfil de competencia, nivel de riesgo y clasificación por recurso
   (no hay rechazo binario).
2. `POST /api/v1/ofertas/adjudicar`: bloquea los recursos de las ofertas elegidas con
   control de concurrencia. Si el inventario no alcanza, responde **409** y hace rollback.
3. `POST /api/v1/proyectos/liberar-recursos`: al terminar las actividades, devuelve los
   recursos al inventario disponible.

## Autenticación

Todos los endpoints de negocio requieren JWT:

1. Ejecutá `POST /auth/login` con tu email y contraseña y copiá el `access_token`.
2. Presioná **Authorize** (arriba a la derecha), pegá el token y confirmá.

## Convenciones

- Los IDs (`id_emergencia`, `id_oferta`, `id_ong`, `id_recurso`) son los de la BD local
  y deben ser enteros mayores a 0.
- Las cantidades son enteros mayores a 0.
- Los timestamps están en UTC (formato ISO 8601 con sufijo `Z`).
- Un campo desconocido o un valor fuera de dominio devuelve **422**.

## Códigos de error

| Código | Significado |
|---|---|
| 401 | Token JWT ausente, inválido o expirado |
| 404 | ONG, recurso, oferta o emergencia inexistente |
| 409 | Inventario insuficiente al adjudicar |
| 422 | El JSON no cumple el contrato |
| 503 | Base de datos o autenticación no disponibles / no configuradas |
"""