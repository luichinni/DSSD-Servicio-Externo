# Guía de Testing Standalone de la API Externa (RescueSync)

Esta guía contiene comandos `curl` listos para copiar y pegar y payloads JSON puros para testear `DSSD-Servicio-Externo` de manera aislada (sin depender de Bonita BPM ni de Flask).

---

## 1. Configuración Previa del Entorno

### 1.1. Variable de URL Base

Define la URL base de la API en tu terminal (en local o en cloud):

```bash
# Para pruebas locales directas:
export API_BASE_URL="http://localhost:8000"

# O si estás apuntando al despliegue en la nube:
# export API_BASE_URL="https://tu-dominio-cloud.ejemplo.com"
```

*(En PowerShell de Windows, puedes usar: `$env:API_BASE_URL = "http://localhost:8000"`)*

---

### 1.2. Creación del Usuario Operador con el CLI Oficial

La API requiere un usuario registrado en PostgreSQL para emitir tokens JWT. Puedes crear uno interactivamente dentro del contenedor Docker:

```bash
docker compose exec api python -m app.cli.create_user
```

**Parámetros requeridos por el CLI:**
* **Email:** `operador@emergencias.gob.ar` (o cualquier email válido)
* **Contraseña:** Mínimo **12 caracteres** (ejemplo: `PasswordSegura123!`)
* **Confirmación de contraseña:** Misma clave.

---

### 1.3. Carga de Datos Seed (ONGs, Recursos, Inventario y Certificaciones)

Si la base de datos está vacía o recién inicializada, carga los datos demo preconfigurados:

```bash
docker compose exec api python -m app.cli.seed_certificaciones_demo
```

**Datos cargados en el sistema:**
* **ONG 3 (Habilitada):**
  * Recurso 10 (*Bote de rescate demo*): Stock total = 100, disponible = 80. Certificación vigente en desastre `hidrologico`, rol `lote_principal`, riesgo `alto`.
  * Recurso 12 (*Personal de apoyo demo*): Stock total = 10, disponible = 10. Certificación vigente en desastre `hidrologico`, rol `apoyo_secundario`, riesgo `alto`.
* **ONG 4 (Habilitada):**
  * Recurso 10: Certificación **vencida** para desastre `hidrologico` (ideal para probar error 404).
  * Recurso 12: Certificación vigente rol `apoyo_secundario`, riesgo `bajo`.
* **ONG 1 (Habilitada):** Stock abundante (Recurso 10 = 500, Recurso 12 = 200).

---

## 2. Autenticación y Obtención del Token JWT

### 2.1. Iniciar Sesión (`POST /api/v1/auth/login`)

```bash
curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "operador@emergencias.gob.ar",
    "password": "PasswordSegura123!"
  }'
```

**Respuesta esperada (HTTP 200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2.2. Exportar el Token para los Siguientes Pasos

En terminal Bash:
```bash
export TOKEN=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "operador@emergencias.gob.ar",
    "password": "PasswordSegura123!"
  }' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Verificar que se guardó correctamente:
echo "Token: $TOKEN"
```

*(En PowerShell: `$TOKEN = (Invoke-RestMethod -Method Post -Uri "$env:API_BASE_URL/api/v1/auth/login" -Body '{"email":"operador@emergencias.gob.ar","password":"PasswordSegura123!"}' -ContentType "application/json").access_token`)*

### 2.3. Verificar Usuario Autenticado (`GET /api/v1/auth/me`)

```bash
curl -s -X GET "$API_BASE_URL/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 3. Consultas de Catálogo y Disponibilidad

### 3.1. Listar ONGs Habilitadas (`GET /api/v1/ongs/habilitadas`)

```bash
curl -s -X GET "$API_BASE_URL/api/v1/ongs/habilitadas" \
  -H "Authorization: Bearer $TOKEN"
```

### 3.2. Consultar Disponibilidad Global de Recursos (`GET /api/v1/recursos/disponibilidad`)

```bash
# Disponibilidad total sin filtros:
curl -s -X GET "$API_BASE_URL/api/v1/recursos/disponibilidad" \
  -H "Authorization: Bearer $TOKEN"

# Filtrar por ONG específica (?id_ong=3):
curl -s -X GET "$API_BASE_URL/api/v1/recursos/disponibilidad?id_ong=3" \
  -H "Authorization: Bearer $TOKEN"

# Filtrar por Recurso específico (?recurso_id=10):
curl -s -X GET "$API_BASE_URL/api/v1/recursos/disponibilidad?recurso_id=10" \
  -H "Authorization: Bearer $TOKEN"
```

### 3.3. Registrar una Nueva ONG (`POST /api/v1/ongs`)

```bash
curl -s -X POST "$API_BASE_URL/api/v1/ongs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_ong": 90,
    "nombre": "Cruz de Ayuda Comunitaria",
    "descripcion": "ONG especializada en logística y socorro urbano"
  }'
```

---

## 4. Flujo Core Exitoso Completo (Validación -> Adjudicación -> Liberación)

Simulación del ciclo de vida para la emergencia `id_emergencia = 501`.

### Paso 1: Validar Ofertas por Competencias (`POST /api/v1/ofertas/validar`)

Evalúa sin rechazo binario la capacidad de la ONG 3 frente a un evento hidrológico de gravedad alta:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/ofertas/validar" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_emergencia": 501,
    "tipo_desastre": "hidrologico",
    "gravedad": "alto",
    "ofertas": [
      {
        "id_oferta": 15,
        "es_conjunta": false,
        "id_ong": 3,
        "recursos": [
          { "id_recurso": 10, "cantidad_ofrecida": 50 },
          { "id_recurso": 12, "cantidad_ofrecida": 5 }
        ]
      }
    ]
  }'
```

**Respuesta esperada (HTTP 200 OK):**
```json
{
  "id_emergencia": 501,
  "estado_general": "validado",
  "ofertas_validadas": [
    {
      "id_oferta": 15,
      "id_ong": 3,
      "perfil_competencia_ong": "Avanzado",
      "nivel_riesgo_permitido": "Alto",
      "recursos_evaluados": [
        {
          "id_recurso": 10,
          "cantidad_validada": 50,
          "clasificacion": "lote_principal",
          "observacion": "Habilitación vigente para actuar como responsable principal."
        },
        {
          "id_recurso": 12,
          "cantidad_validada": 5,
          "clasificacion": "apoyo_secundario",
          "observacion": "Apoyo bajo supervisión, únicamente en tareas de riesgo hasta Alto. No habilita tareas que superen ese nivel."
        }
      ]
    }
  ]
}
```

---

### Paso 2: Adjudicar y Bloquear Recursos (`POST /api/v1/ofertas/adjudicar`)

El Municipio adjudica la oferta y la API compromete transaccionalmente el stock en PostgreSQL:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/ofertas/adjudicar" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_emergencia": 501,
    "ofertas_adjudicadas": [
      {
        "id_oferta": 15,
        "id_ong": 3,
        "recursos": [
          { "id_recurso": 10, "cantidad_adjudicada": 50 }
        ]
      }
    ]
  }'
```

**Respuesta esperada (HTTP 200 OK):**
```json
{
  "id_emergencia": 501,
  "estado": "bloqueo_exitoso",
  "mensaje": "Los recursos han sido comprometidos transaccionalmente a nivel nacional.",
  "timestamp_bloqueo": "2026-10-22T15:30:00Z",
  "ofertas_adjudicadas": [
    {
      "id_oferta": 15,
      "id_ong": 3,
      "estado": "adjudicada"
    }
  ],
  "ofertas_rechazadas": []
}
```

*(Si vuelves a enviar exactamente la misma petición, responderá HTTP 200 OK de forma **idempotente** sin descontar doble stock).*

---

### Paso 3: Liberar Recursos al Cierre del Proyecto (`POST /api/v1/proyectos/liberar-recursos`)

Al concluir las tareas de campo, se destraban los recursos restituyéndolos al inventario disponible:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/proyectos/liberar-recursos" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_emergencia": 501,
    "id_ong": 3,
    "motivo_cierre": "finalizacion_tareas",
    "recursos_a_liberar": [
      { "id_recurso": 10, "cantidad_liberada": 50 }
    ]
  }'
```

**Respuesta esperada (HTTP 200 OK):**
```json
{
  "estado": "liberacion_exitosa",
  "id_ong": 3,
  "mensaje": "Recursos liberados. Disponibilidad global actualizada.",
  "total_recursos_liberados": 50
}
```

---

## 5. Pruebas de Casos de Error y Validaciones Negativas

### 5.1. Error HTTP 409 Conflict: Falta Total de Stock en Adjudicación

Intentar adjudicar una cantidad excesiva (ej. 99,999 botes a la ONG 3):

```bash
curl -s -i -X POST "$API_BASE_URL/api/v1/ofertas/adjudicar" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_emergencia": 502,
    "ofertas_adjudicadas": [
      {
        "id_oferta": 99,
        "id_ong": 3,
        "recursos": [
          { "id_recurso": 10, "cantidad_adjudicada": 99999 }
        ]
      }
    ]
  }'
```

**Respuesta esperada (HTTP 409 Conflict):**
```json
{
  "detail": {
    "id_emergencia": 502,
    "estado": "bloqueo_fallido",
    "mensaje": "Ninguna oferta pudo ser adjudicada por falta de stock o inconsistencias.",
    "ofertas_rechazadas": [
      {
        "id_oferta": 99,
        "id_ong": 3,
        "motivo": "No fue posible adjudicar todos los recursos de la oferta",
        "recursos_sin_stock": [
          {
            "id_recurso": 10,
            "cantidad_solicitada": 99999,
            "cantidad_disponible": 80,
            "motivo": "stock_insuficiente"
          }
        ]
      }
    ]
  }
}
```

---

### 5.2. Error HTTP 404 Not Found: Certificación Vencida en Validación

La ONG 4 tiene la certificación del recurso 10 vencida:

```bash
curl -s -i -X POST "$API_BASE_URL/api/v1/ofertas/validar" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_emergencia": 503,
    "tipo_desastre": "hidrologico",
    "gravedad": "alto",
    "ofertas": [
      {
        "id_oferta": 20,
        "es_conjunta": false,
        "id_ong": 4,
        "recursos": [
          { "id_recurso": 10, "cantidad_ofrecida": 5 }
        ]
      }
    ]
  }'
```

**Respuesta esperada (HTTP 404 Not Found):**
```json
{
  "detail": "No se encontró certificación vigente aplicable para la ONG 4, recurso 10 y desastre hidrologico."
}
```

---

### 5.3. Error HTTP 404 Not Found: Liberación sin Compromisos Activos

Intentar liberar recursos de una emergencia inexistente o ya liberada:

```bash
curl -s -i -X POST "$API_BASE_URL/api/v1/proyectos/liberar-recursos" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_emergencia": 999999,
    "id_ong": 3,
    "motivo_cierre": "finalizacion_tareas",
    "recursos_a_liberar": []
  }'
```

**Respuesta esperada (HTTP 404 Not Found):**
```json
{
  "detail": "No se encontraron recursos comprometidos activos para la emergencia 999999 y ONG 3."
}
```

---

### 5.4. Error HTTP 401 Unauthorized: Solicitud sin Token o con Token Inválido

```bash
# Sin header Authorization:
curl -s -i -X GET "$API_BASE_URL/api/v1/ongs/habilitadas"

# Con token malformado:
curl -s -i -X GET "$API_BASE_URL/api/v1/ongs/habilitadas" \
  -H "Authorization: Bearer token_falso_invalido"
```

**Respuesta esperada (HTTP 401 Unauthorized):**
```json
{
  "detail": "Invalid or expired authentication token"
}
```

---

### 5.5. Error HTTP 422 Unprocessable Entity: Valor de Enum Inválido

Enviar `gravedad: "alta"` (femenino) o `tipo_desastre: "inundacion"`:

```bash
curl -s -i -X POST "$API_BASE_URL/api/v1/ofertas/validar" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_emergencia": 504,
    "tipo_desastre": "inundacion",
    "gravedad": "alta",
    "ofertas": []
  }'
```

**Respuesta esperada (HTTP 422 Unprocessable Entity):**
Indica los valores válidos esperados (`bajo`, `medio`, `alto`, `critico` y `hidrologico`, `geologico`, etc.).

---

## 6. Monitoreo y Verificación de Salud

```bash
# Liveness probe:
curl -s "$API_BASE_URL/health"
# {"status":"ok"}

# Readiness probe (verifica conexión viva a PostgreSQL):
curl -s "$API_BASE_URL/health/db"
# {"status":"ok","database":"connected"}
```
