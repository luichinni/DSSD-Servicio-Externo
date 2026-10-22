# Especificación de API Externa - Sistema Nacional RescueSync (Entrega 3)

Este documento detalla la arquitectura, endpoints, estructuras de comunicación (JSON) y los detalles técnicos de implementación para la API del Sistema Nacional. Esta API gestiona la validación de competencias, el bloqueo concurrente y la liberación de recursos en PostgreSQL.

---

## 1. Stack Tecnológico

La API está construida con **FastAPI** y **SQLAlchemy 2.0** sobre **PostgreSQL 15**.

*   **Documentación Interactiva:** FastAPI genera automáticamente la documentación OpenAPI en `/docs` (Swagger UI) y `/redoc`.
*   **Validación de Modelos:** Pydantic valida estrictamente los JSON entrantes, retornando HTTP 422 si hay discrepancias de tipos o valores de enums inválidos.
*   **Compatibilidad con Bonita BPM:** Los endpoints core (`validar`, `adjudicar`, `liberar-recursos`) soportan tanto payloads JSON estándar como strings JSON escapados/serializados enviados por Bonita.

---

## 2. Endpoints y Detalles de Implementación

### 2.1. Autenticación y Usuarios
*   **Endpoint:** `POST /api/v1/auth/login`
*   **Propósito:** Autentica credenciales del sistema cliente o Bonita y emite un token Bearer JWT.
*   **Seguridad:** Público.
*   **Estructura del Request:**
    ```json
    {
      "email": "usuario@ejemplo.com",
      "password": "password_segura_123"
    }
    ```
*   **Respuesta Exitosa (200 OK):**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1Ni...",
      "token_type": "bearer"
    }
    ```
*   **Endpoint complementario:** `GET /api/v1/auth/me` (Requiere JWT) - Retorna datos del usuario autenticado (`id`, `email`, `is_active`).

### 2.2. Catálogo y ONGs

#### 2.2.1. Consulta de ONGs Habilitadas
*   **Endpoint:** `GET /api/v1/ongs/habilitadas`
*   **Propósito:** Lista todas las organizaciones habilitadas junto con el resumen de sus certificaciones activas y vigentes.
*   **Seguridad:** Requiere JWT (`Authorization: Bearer <token>`).
*   **Respuesta Exitosa (200 OK):**
    ```json
    {
      "total": 1,
      "ongs": [
        {
          "id_ong": 3,
          "nombre": "ONG Demo 3",
          "habilitada": true,
          "certificaciones": [
            "Bote de rescate demo: hidrologico, lote_principal, riesgo alto",
            "Personal de apoyo demo: hidrologico, apoyo_secundario, riesgo alto"
          ]
        }
      ]
    }
    ```

#### 2.2.2. Disponibilidad Global de Recursos
*   **Endpoint:** `GET /api/v1/recursos/disponibilidad`
*   **Propósito:** Consulta el inventario disponible y comprometido a nivel nacional.
*   **Seguridad:** Requiere JWT.
*   **Query Parameters (opcionales):**
    *   `recurso_id` (int > 0): Filtra por ID de recurso.
    *   `id_ong` (int > 0): Filtra por ID de ONG.
*   **Respuesta Exitosa (200 OK):**
    ```json
    {
      "total": 1,
      "recursos": [
        {
          "id_ong": 3,
          "id_recurso": 10,
          "nombre_recurso": "Bote de rescate demo",
          "inventario_actual": 80,
          "cantidad_comprometida": 20
        }
      ]
    }
    ```

#### 2.2.3. Registro de ONGs
*   **Endpoint:** `POST /api/v1/ongs`
*   **Propósito:** Registra una nueva ONG con el ID correspondiente a la aplicación local.
*   **Seguridad:** Requiere JWT.
*   **Respuesta:** `201 Created` si se crea exitosamente; `409 Conflict` si el `id_ong` ya se encuentra registrado.

---

### 2.3. Core: Validación Externa por Competencias

*   **Endpoint:** `POST /api/v1/ofertas/validar`
*   **Propósito:** Evalúa las ofertas recibidas según las certificaciones oficiales de cada ONG sin aplicar un rechazo binario (True/False).
*   **Seguridad:** Requiere JWT.
*   **Enums Obligatorios:**
    *   `tipo_desastre`: `"geologico"`, `"meteorologico"`, `"hidrologico"`, `"biologico"`, `"incendio_forestal"`.  
        *(Nota: Valores como `"inundacion"` no son válidos; debe utilizarse `"hidrologico"`).*
    *   `gravedad`: `"bajo"`, `"medio"`, `"alto"`, `"critico"`.  
        *(Nota: Debe enviarse en género masculino `"alto"`; `"alta"` produce error 422).*
*   **Reglas de Evaluación:**
    1. Si la ONG cuenta con habilitación de `lote_principal` y su nivel de riesgo máximo cubre la gravedad del evento, el recurso se clasifica como `lote_principal`.
    2. Si la certificación es de rol secundario o el riesgo máximo no cubre la gravedad, se clasifica como `apoyo_secundario` con observaciones específicas.
    3. Si alguna ONG no existe, no está habilitada o carece de certificación vigente para el recurso y tipo de desastre, la API rechaza la solicitud completa con HTTP 404 (`ReferenciaNoDisponible` o `CertificacionNoEncontrada`).
    4. Perfil de competencia global resultante: `"Avanzado"`, `"Intermedio"` o `"Basico"`.
    5. Nivel de riesgo permitido devuelto: `"Bajo"`, `"Medio"` o `"Alto"`.

---

### 2.4. Core: Adjudicación y Bloqueo de Recursos (Control de Concurrencia)

*   **Endpoint:** `POST /api/v1/ofertas/adjudicar`
*   **Propósito:** Bloquea y descuenta inventario disponible ante ofertas seleccionadas, garantizando consistencia transaccional bajo concurrencia.
*   **Seguridad:** Requiere JWT.
*   **Detalles Técnicos:**
    *   **Locking:** Utiliza `SELECT ... FOR UPDATE` (`.with_for_update()`) bloqueando los pares `(id_ong, id_recurso)` en orden determinista (`sorted`) para prevenir *deadlocks*.
    *   **Idempotencia:** Si un compromiso ya fue registrado previamente para la misma emergencia y oferta con idéntica cantidad en estado `COMPROMETIDO`, se considera exitoso sin duplicar el descuento de stock.
    *   **Comportamiento de Stock:**
        *   **Bloqueo Exitoso (HTTP 200):** Todas las ofertas disponen de stock suficiente. Se descuenta `cantidad_disponible` y se inserta el registro en `compromisos_recursos`.
        *   **Bloqueo Parcial (HTTP 200):** Se adjudican aquellas ofertas con inventario suficiente y se discriminan las rechazadas en `ofertas_rechazadas`.
        *   **Bloqueo Fallido (HTTP 409 Conflict):** Ninguna oferta pudo ser adjudicada. Se ejecuta `rollback()` y se devuelve el detalle de rechazos por falta de stock.

---

### 2.5. Core: Liberación y Cierre de Proyecto

*   **Endpoint:** `POST /api/v1/proyectos/liberar-recursos`
*   **Propósito:** Marca el fin de actividades destrabando y reintegrando los recursos comprometidos al inventario nacional.
*   **Seguridad:** Requiere JWT.
*   **Detalles Técnicos:**
    *   Busca todos los compromisos en estado `COMPROMETIDO` asociados a la pareja `(id_emergencia, id_ong)`.
    *   Bloquea transaccionalmente las filas de inventario involucradas con `.with_for_update()`.
    *   Restaura `cantidad_disponible` (acotado a `cantidad_total` para prevenir inconsistencias) y actualiza el estado de los compromisos a `LIBERADO` con `fecha_liberacion`.
    *   *(Nota: La lista `recursos_a_liberar` del payload es opcional; la liberación restituye la totalidad de los recursos comprometidos activos para esa emergencia y ONG).*
    *   **HTTP 404 Not Found:** Si no existen compromisos activos para la emergencia y ONG indicadas (por ejemplo, si ya fueron liberados previamente).

---

### 2.6. Monitoreo y Salud del Servicio
*   `GET /health`: Liveness probe (retorna `{"status": "ok"}`).
*   `GET /health/db`: Readiness probe verificando conectividad real con PostgreSQL (`{"status": "ok", "database": "connected"}`).

---

## 3. Estructuras de Comunicación (JSON Payloads para Bonita)

Bonita puede enviar los payloads como objetos JSON nativos o como strings JSON serializados.

### 3.1. Payload: Validación de Ofertas

**Enviado a la API (`POST /api/v1/ofertas/validar`):**
```json
{
  "id_emergencia": 101,
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
}
```

**Respuesta exitosa de la API (HTTP 200 OK):**
```json
{
  "id_emergencia": 101,
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

**Respuesta ante certificación faltante o no vigente (HTTP 404 Not Found):**
```json
{
  "detail": "No se encontró certificación vigente aplicable para la ONG 4, recurso 10 y desastre hidrologico."
}
```

---

### 3.2. Payload: Adjudicación / Bloqueo de Recursos

**Enviado a la API (`POST /api/v1/ofertas/adjudicar`):**
```json
{
  "id_emergencia": 101,
  "ofertas_adjudicadas": [
    {
      "id_oferta": 15,
      "id_ong": 3,
      "recursos": [
        { "id_recurso": 10, "cantidad_adjudicada": 50 }
      ]
    }
  ]
}
```

**Respuesta exitosa total (HTTP 200 OK):**
```json
{
  "id_emergencia": 101,
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

**Respuesta parcial (HTTP 200 OK - Algunas con stock y otras rechazadas):**
```json
{
  "id_emergencia": 101,
  "estado": "bloqueo_parcial",
  "mensaje": "Se adjudicaron parcialmente las ofertas con disponibilidad suficiente.",
  "timestamp_bloqueo": "2026-10-22T15:30:00Z",
  "ofertas_adjudicadas": [
    {
      "id_oferta": 15,
      "id_ong": 3,
      "estado": "adjudicada"
    }
  ],
  "ofertas_rechazadas": [
    {
      "id_oferta": 16,
      "id_ong": 3,
      "motivo": "No fue posible adjudicar todos los recursos de la oferta",
      "recursos_sin_stock": [
        {
          "id_recurso": 12,
          "cantidad_solicitada": 9999,
          "cantidad_disponible": 10,
          "motivo": "stock_insuficiente"
        }
      ]
    }
  ]
}
```

**Respuesta ante stock insuficiente total (HTTP 409 Conflict):**
```json
{
  "detail": {
    "id_emergencia": 101,
    "estado": "bloqueo_fallido",
    "mensaje": "Ninguna oferta pudo ser adjudicada por falta de stock o inconsistencias.",
    "ofertas_rechazadas": [
      {
        "id_oferta": 15,
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

### 3.3. Payload: Fin de Actividades / Liberación

**Enviado a la API (`POST /api/v1/proyectos/liberar-recursos`):**
```json
{
  "id_emergencia": 101,
  "id_ong": 3,
  "motivo_cierre": "finalizacion_tareas",
  "recursos_a_liberar": [
    { "id_recurso": 10, "cantidad_liberada": 50 }
  ]
}
```

**Respuesta exitosa (HTTP 200 OK):**
```json
{
  "estado": "liberacion_exitosa",
  "id_ong": 3,
  "mensaje": "Recursos liberados. Disponibilidad global actualizada.",
  "total_recursos_liberados": 50
}
```

**Respuesta si no hay recursos comprometidos activos (HTTP 404 Not Found):**
```json
{
  "detail": "No se encontraron recursos comprometidos activos para la emergencia 101 y ONG 3."
}
```

---

## 4. Tabla Resumen de Códigos HTTP

| Código | Descripción y Cuándo se Emite |
| :--- | :--- |
| **200 OK** | Operación exitosa (`login`, `validar`, consultas GET, `liberar-recursos`, o `adjudicar` total/parcial). |
| **201 Created** | Creación exitosa de recurso (`POST /api/v1/ongs`). |
| **401 Unauthorized** | Token ausente, inválido o expirado en endpoints protegidos; o credenciales incorrectas en login. |
| **404 Not Found** | ONG, recurso o certificación vigente no encontrada en validación; o sin compromisos activos al liberar. |
| **409 Conflict** | Conflicto por falta total de stock en adjudicación (`bloqueo_fallido`) o ID de ONG duplicado en registro. |
| **422 Unprocessable** | Error de formato/validación en payload JSON (ej. `gravedad: "alta"` en lugar de `"alto"`, tipos de dato erróneos). |
| **503 Unavailable** | Base de datos PostgreSQL no disponible o error de configuración JWT. |