# Especificación de API Externa - Sistema Nacional RescueSync (Entrega 3)

Este documento detalla la arquitectura, endpoints, estructuras de comunicación (JSON) y los detalles técnicos de implementación para la API del Sistema Nacional. Esta API gestionará la validación, el bloqueo concurrente y la liberación de recursos en PostgreSQL.

---

## 1. Stack Tecnológico Sugerido

Se recomienda utilizar **FastAPI** junto con **SQLAlchemy** (para PostgreSQL). 

*   **Motivo:** FastAPI genera automáticamente la documentación Swagger (OpenAPI) basándose en los modelos de datos (Pydantic). Esto elimina la necesidad de mantener el Swagger a mano, reduce los tiempos de desarrollo, y valida automáticamente la estructura de los JSON que enviará Bonita (rechazando con un error 422 si la estructura no es exacta).

---

## 2. Endpoints y Detalles de Implementación (Guía para Developers)

### 2.1. Autenticación
*   **Endpoint:** `POST /api/v1/auth/login`
*   **Propósito:** Recibe credenciales del sistema cliente (o Bonita) y retorna un token JWT.
*   **Seguridad:** Público.
*   **Detalles de Implementación:**
    *   **Lógica:** Recibir credenciales (ej. `client_id` y `client_secret` o `username` y `password` en el body).
    *   Validar contra una tabla de usuarios centralizados en PostgreSQL.
    *   Generar un token JWT utilizando una librería como `python-jose` (en FastAPI) o `PyJWT`.
*   **Respuesta Exitosa:** `{ "access_token": "eyJhb...", "token_type": "bearer" }`

### 2.2. Catálogo y ONGs
*   **Endpoints:** 
    *   `GET /api/v1/ongs/habilitadas`
    *   `GET /api/v1/recursos/disponibilidad`
*   **Propósito:** Devuelve el listado de ONGs registradas, su estado de habilitación, y permite consultar la disponibilidad global de recursos.
*   **Seguridad:** Requiere JWT (`Depends(get_current_user)` en FastAPI).
*   **Detalles de Implementación:**
    *   Implementar métodos GET que consulten las vistas o tablas de PostgreSQL del Sistema Nacional y retornen el listado.
    *   Permitir *query parameters* para filtrar (ej. `?recurso_id=10`).

### 2.3. Core: Validación Externa por Competencias
*   **Endpoint:** `POST /api/v1/ofertas/validar`
*   **Propósito:** Evalúa las ofertas recibidas según las certificaciones de la ONG. 
*   **Seguridad:** Requiere JWT.
*   **Detalles de Implementación:**
    *   **Lógica:** Deserializar el JSON entrante enviado por Bonita.
    *   Por cada ONG, consultar la base de datos centralizada (ej. tabla de certificaciones).
    *   **Regla de Negocio (Enunciado):** NO aplicar un rechazo binario (True/False). Se debe cruzar el recurso ofrecido con la habilitación de la ONG y asignar un perfil de competencia (ej: "Lote Principal", "Apoyo Secundario") y nivel de riesgo.

### 2.4. Core: Adjudicación y Bloqueo de Recursos (Control de Concurrencia)
*   **Endpoint:** `POST /api/v1/ofertas/adjudicar`
*   **Propósito:** Recibe las ofertas seleccionadas por el Municipio y ejecuta un bloqueo para evitar sobre-asignaciones.
*   **Seguridad:** Requiere JWT.
*   **Detalles de Implementación (CRÍTICO):**
    *   **Lógica de Bloqueo (Locking):** Para prevenir *race conditions* exigidas por el TP, implementar un bloqueo transaccional en PostgreSQL.
    *   **En SQLAlchemy:** Utilizar `.with_for_update()` en la consulta.
        *   *Ejemplo:* `db.query(InventarioNacional).filter_by(id_ong=X, id_recurso=Y).with_for_update().first()`
    *   Verificar si `inventario_actual >= cantidad_adjudicada`. Si es así, restar y hacer `commit()`. Si no alcanza, hacer `rollback()` y devolver HTTP 409 (Conflict).
    *   Registrar este compromiso asociándolo al `id_emergencia`.

### 2.5. Core: Liberación y Cierre de Proyecto
*   **Endpoint:** `POST /api/v1/proyectos/liberar-recursos`
*   **Propósito:** Marca el fin de actividades destrabando los recursos en la BD nacional.
*   **Seguridad:** Requiere JWT.
*   **Detalles de Implementación:**
    *   **Lógica:** Buscar los recursos comprometidos para el `id_emergencia` y la ONG en cuestión.
    *   Sumar nuevamente las cantidades al inventario disponible (o cambiar el estado de "COMPROMETIDO" a "DISPONIBLE").
    *   Envolver la operación en una transacción para asegurar consistencia y retornar HTTP 200 OK.

---

## 3. Estructuras de Comunicación (JSON Payloads para Bonita)

Bonita hará de "pasamanos" enviando y recibiendo *strings largos* (JSON). La estructura debe usar los IDs exactos de la BD local (`id_oferta`, `id_ong`, `id_recurso`).

### 3.1. Payload: Validación de Ofertas

**Lo que envía Bonita a la API (`POST /api/v1/ofertas/validar`):**
```json
{
  "id_emergencia": 101,
  "tipo_desastre": "inundacion",
  "gravedad": "alta",
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

**Lo que retorna la API a Bonita:**
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
          "observacion": "Capacidad óptima"
        },
        { 
          "id_recurso": 12, 
          "cantidad_validada": 5, 
          "clasificacion": "apoyo_secundario",
          "observacion": "Requiere supervisión regional"
        }
      ]
    }
  ]
}
```

### 3.2. Payload: Adjudicación / Bloqueo de Recursos

**Lo que envía Bonita a la API (`POST /api/v1/ofertas/adjudicar`):**
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

**Lo que retorna la API a Bonita:**
```json
{
  "id_emergencia": 101,
  "estado": "bloqueo_exitoso",
  "mensaje": "Los recursos han sido comprometidos transaccionalmente a nivel nacional.",
  "timestamp_bloqueo": "2026-10-12T15:30:00Z"
}
```

### 3.3. Payload: Fin de Actividades / Liberación

**Lo que envía Bonita a la API (`POST /api/v1/proyectos/liberar-recursos`):**
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

**Lo que retorna la API a Bonita:**
```json
{
  "estado": "liberacion_exitosa",
  "id_ong": 3,
  "mensaje": "Recursos liberados. Disponibilidad global actualizada."
}
```