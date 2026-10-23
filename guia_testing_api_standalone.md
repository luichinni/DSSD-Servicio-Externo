# Guía de Testing de la API Externa (RescueSync) en Swagger UI

Esta guía está diseñada para que quien corrija o evalúe el sistema pueda realizar las pruebas funcionales de manera interactiva, autónoma y directa a través de **Swagger UI (`/docs`)**, sin necesidad de ejecutar comandos `curl` en terminal.

Se documentan los parámetros requeridos y opcionales de cada endpoint y se proporcionan casos de ejemplo con datos JSON listos para copiar y pegar en la interfaz web de Swagger.

---

## 1. Puesta en Marcha y Carga de Datos Iniciales (Seeds)

Antes de abrir Swagger, ejecutá los siguientes comandos en tu terminal en la raíz de `DSSD-Servicio-Externo` para iniciar los contenedores y sembrar los datos de prueba:

```bash
# 1. Iniciar los contenedores de la API y PostgreSQL
docker compose up -d

# 2. Aplicar las migraciones de base de datos
docker compose exec api alembic upgrade head

# 3. Cargar las semillas de datos (Usuario demo, ONGs, Recursos, Inventario y Certificaciones)
docker compose exec api python -m app.cli.seed_certificaciones_demo
```

### Tabla de Datos Sembrados en el Entorno

| Entidad | ID / Clave | Nombre / Descripción | Estado / Rol / Stock | Certificación / Vigencia |
|---|---|---|---|---|
| **Usuario Operador** | `operador@emergencias.gob.ar` | Usuario de prueba para autenticación | Password: `PasswordSegura123!` | Permite emitir JWT para Swagger |
| **ONG 3** | `id_ong = 3` | ONG Demo 3 | `habilitada = true` | Posee 2 certificaciones vigentes en desastre `hidrologico` |
| ↳ *Inventario Recurso 10* | `id_recurso = 10` | Bote de rescate demo | Total: `100`, Disp: `80`, Compr: `20` | `lote_principal`, riesgo `alto`, perfil `Avanzado` (Vigente +365 días) |
| ↳ *Inventario Recurso 12* | `id_recurso = 12` | Personal de apoyo demo | Total: `10`, Disp: `10`, Compr: `0` | `apoyo_secundario`, riesgo `alto`, perfil `Intermedio` (Vigente +365 días) |
| **ONG 4** | `id_ong = 4` | ONG Demo 4 | `habilitada = true` | Posee 1 certificación vencida y 1 vigente |
| ↳ *Inventario Recurso 10* | `id_recurso = 10` | Bote de rescate demo | Total: `20`, Disp: `15`, Compr: `5` | `lote_principal`, riesgo `alto` (**Vencida hace 1 día**) |
| ↳ *Inventario Recurso 12* | `id_recurso = 12` | Personal de apoyo demo | Total: `10`, Disp: `5`, Compr: `5` | `apoyo_secundario`, riesgo `bajo`, perfil `Basico` (Vigente +365 días) |
| **ONG 5** | `id_ong = 5` | ONG Demo Inhabilitada 5 | `habilitada = false` | Sin certificaciones ni stock (para pruebas de exclusión) |
| **Recurso 20** | `id_recurso = 20` | Generador eléctrico demo | En catálogo nacional | Sin certificación ni inventario (para pruebas de omisión) |

---

## 2. Acceso a Swagger UI y Autenticación con JWT

1. Ingresá desde tu navegador web a la interfaz interactiva de Swagger:  
   **[http://localhost:8000/docs](http://localhost:8000/docs)**
2. Desplegá el tag **Auth** y abrí el endpoint `POST /api/v1/auth/login`.
3. Presioná el botón **Try it out**, pegá las credenciales demo en el **Request body** y presioná **Execute**:
   ```json
   {
     "email": "operador@emergencias.gob.ar",
     "password": "PasswordSegura123!"
   }
   ```
4. En el cuadro de respuesta (HTTP 200), seleccioná y copiá el texto del campo `access_token` (sin las comillas):
   ```text
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
5. Dirigite a la parte superior derecha de la página de Swagger y hacé clic en el botón verde **Authorize** (ícono de candado).
6. En la ventana emergente, pegá el token en el campo **Value** y hacé clic en **Authorize**, luego en **Close**.

> **Nota:** A partir de este paso, Swagger enviará de forma automática el encabezado `Authorization: Bearer <token>` en todas las peticiones a endpoints protegidos.

---

## 3. Endpoints de Monitoreo y Salud (Health)

### 3.1. `GET /health` - Liveness Probe

Verifica que el proceso uvicorn/FastAPI esté activo y respondiendo solicitudes HTTP.

* **Tag Swagger:** `Health`
* **Requiere Autenticación:** No.

#### Parámetros
*Este endpoint no recibe parámetros.*

#### Caso de Prueba en Swagger
1. Abrí `GET /health` y hacé clic en **Try it out**.
2. Presioná **Execute**.

* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "status": "ok"
  }
  ```

---

### 3.2. `GET /health/db` - Readiness Probe

Verifica la conectividad activa con el motor de base de datos PostgreSQL ejecutando `SELECT 1`.

* **Tag Swagger:** `Health`
* **Requiere Autenticación:** No.

#### Parámetros
*Este endpoint no recibe parámetros.*

#### Caso de Prueba en Swagger
1. Abrí `GET /health/db` y hacé clic en **Try it out**.
2. Presioná **Execute**.

* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "status": "ok"
  }
  ```

---

## 4. Endpoints de Autenticación (Auth)

### 4.1. `POST /api/v1/auth/login` - Inicio de Sesión y Emisión de JWT

Autentica las credenciales del operador y genera un token JWT con vigencia temporal.

* **Tag Swagger:** `Auth`
* **Requiere Autenticación:** No.

#### Parámetros

| Parámetro | Ubicación | Tipo | Requerido | Restricciones / Formato | Descripción |
|---|---|---|---|---|---|
| `email` | Body (JSON) | `string` | **Sí** | Formato de email válido | Correo electrónico del usuario registrado |
| `password` | Body (JSON) | `string` | **Sí** | Mínimo 12 caracteres | Contraseña en texto plano |

#### Caso 1: Inicio de Sesión Exitoso (HTTP 200 OK)
* **Request body:**
  ```json
  {
    "email": "operador@emergencias.gob.ar",
    "password": "PasswordSegura123!"
  }
  ```
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```

#### Caso 2: Credenciales Inválidas (HTTP 401 Unauthorized)
* **Request body:**
  ```json
  {
    "email": "operador@emergencias.gob.ar",
    "password": "ClaveIncorrecta999!"
  }
  ```
* **Código HTTP esperado:** `401 Unauthorized`
* **Respuesta esperada:**
  ```json
  {
    "detail": "Incorrect email or password"
  }
  ```

---

### 4.2. `GET /api/v1/auth/me` - Perfil de Usuario Autenticado

Retorna los datos de identidad del usuario asociado al token JWT actual.

* **Tag Swagger:** `Auth`
* **Requiere Autenticación:** **Sí** (Bearer JWT).

#### Parámetros
*Recibe únicamente el token a través del botón **Authorize** de Swagger.*

#### Caso de Prueba en Swagger
1. Asegurate de haber presionado **Authorize** con un token válido.
2. Abrí `GET /api/v1/auth/me`, hacé clic en **Try it out** y luego en **Execute**.

* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "id": "e4b6c230-...",
    "email": "operador@emergencias.gob.ar"
  }
  ```

---

## 5. Endpoints de Catálogo y ONGs (Catálogo)

### 5.1. `GET /api/v1/ongs/habilitadas` - Listado de ONGs Habilitadas

Consulta todas las organizaciones registradas con estado `habilitada = true` junto con la lista textual de sus certificaciones activas no vencidas. Excluye automáticamente a las ONGs inhabilitadas (como la ONG 5).

* **Tag Swagger:** `Catálogo`
* **Requiere Autenticación:** **Sí** (Bearer JWT).

#### Parámetros
*Este endpoint no recibe parámetros.*

#### Caso de Prueba en Swagger
1. Abrí `GET /api/v1/ongs/habilitadas`, hacé clic en **Try it out** y presioná **Execute**.

* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "total": 2,
    "ongs": [
      {
        "id_ong": 3,
        "nombre": "ONG Demo 3",
        "habilitada": true,
        "certificaciones": [
          "Bote de rescate demo: hidrologico, lote_principal, riesgo alto",
          "Personal de apoyo demo: hidrologico, apoyo_secundario, riesgo alto"
        ]
      },
      {
        "id_ong": 4,
        "nombre": "ONG Demo 4",
        "habilitada": true,
        "certificaciones": [
          "Personal de apoyo demo: hidrologico, apoyo_secundario, riesgo bajo"
        ]
      }
    ]
  }
  ```
* **Criterio de validación:** Se observa que la ONG 4 no lista el Recurso 10 (porque su certificación está vencida) y que la ONG 5 no aparece por estar inhabilitada.

---

### 5.2. `GET /api/v1/recursos/disponibilidad` - Consulta de Inventario y Compromisos

Consulta el inventario actual disponible y la cantidad comprometida en emergencias activas a nivel nacional. Permite filtrar opcionalmente por ONG o por recurso.

* **Tag Swagger:** `Catálogo`
* **Requiere Autenticación:** **Sí** (Bearer JWT).

#### Parámetros

| Parámetro | Ubicación | Tipo | Requerido | Restricciones | Descripción |
|---|---|---|---|---|---|
| `id_ong` | Query | `integer` | No | Entero mayor a 0 (`gt=0`) | Filtra el inventario por una ONG específica |
| `recurso_id` | Query | `integer` | No | Entero mayor a 0 (`gt=0`) | Filtra por un recurso específico |

#### Caso 1: Consulta General sin Filtros
* **Instrucciones:** Dejar los campos `id_ong` y `recurso_id` vacíos y presionar **Execute**.
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "total": 4,
    "recursos": [
      {
        "id_ong": 3,
        "id_recurso": 10,
        "nombre_recurso": "Bote de rescate demo",
        "inventario_actual": 80,
        "cantidad_comprometida": 20
      },
      {
        "id_ong": 3,
        "id_recurso": 12,
        "nombre_recurso": "Personal de apoyo demo",
        "inventario_actual": 10,
        "cantidad_comprometida": 0
      },
      {
        "id_ong": 4,
        "id_recurso": 10,
        "nombre_recurso": "Bote de rescate demo",
        "inventario_actual": 15,
        "cantidad_comprometida": 5
      },
      {
        "id_ong": 4,
        "id_recurso": 12,
        "nombre_recurso": "Personal de apoyo demo",
        "inventario_actual": 5,
        "cantidad_comprometida": 5
      }
    ]
  }
  ```

#### Caso 2: Filtrar por ONG Específica (`id_ong = 3`)
* **Parámetros Query:** `id_ong: 3` (dejar `recurso_id` vacío).
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:** Devuelve solo los 2 recursos de la ONG 3 (`total: 2`).

#### Caso 3: Filtrar por Recurso Específico (`recurso_id = 10`)
* **Parámetros Query:** `recurso_id: 10` (dejar `id_ong` vacío).
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:** Devuelve el stock del Recurso 10 para todas las ONGs habilitadas (`total: 2`).

---

### 5.3. `POST /api/v1/ongs` - Registrar Nueva ONG en Catálogo Nacional

Permite dar de alta una ONG en el catálogo nacional preservando el ID asignado por el sistema municipal.

* **Tag Swagger:** `Catálogo`
* **Requiere Autenticación:** **Sí** (Bearer JWT).

#### Parámetros

| Parámetro | Ubicación | Tipo | Requerido | Restricciones | Descripción |
|---|---|---|---|---|---|
| `id_ong` | Body (JSON) | `integer` | **Sí** | Entero mayor a 0 | Identificador numérico de la ONG |
| `nombre` | Body (JSON) | `string` | **Sí** | Entre 1 y 150 caracteres | Nombre oficial de la organización |
| `descripcion` | Body (JSON) | `string` | No | Texto libre | Detalle de actividades o alcance |

#### Caso 1: Alta Exitosa de Nueva ONG (HTTP 201 Created)
* **Request body:**
  ```json
  {
    "id_ong": 90,
    "nombre": "Cruz de Ayuda Comunitaria",
    "descripcion": "Organización especializada en rescate y logística urbana"
  }
  ```
* **Código HTTP esperado:** `201 Created`
* **Respuesta esperada:**
  ```json
  {
    "id_ong": 90,
    "nombre": "Cruz de Ayuda Comunitaria",
    "habilitada": true,
    "certificaciones": []
  }
  ```

#### Caso 2: Conflicto por ID de ONG Duplicado (HTTP 409 Conflict)
* **Request body:** Intentar registrar una ONG con un ID que ya existe en la base (ejemplo `id_ong: 3`):
  ```json
  {
    "id_ong": 3,
    "nombre": "ONG Repetida",
    "descripcion": "Intento de duplicación de ID"
  }
  ```
* **Código HTTP esperado:** `409 Conflict`
* **Respuesta esperada:**
  ```json
  {
    "detail": "El ID de ONG ya está registrado."
  }
  ```

---

## 6. Validación de Ofertas por Competencias (Ofertas)

### `POST /api/v1/ofertas/validar`

Evalúa ofertas de recursos presentadas por ONGs frente a un escenario de emergencia. Comprueba certificaciones vigentes, rol autorizado (`lote_principal` o `apoyo_secundario`), riesgo cubierto y perfil resultante sin realizar rechazo binario ni afectar stock.

* **Comportamiento ante recursos no certificados:** Si un recurso carece de certificación vigente o aplicable al desastre, **se omite de la respuesta**. Si una oferta queda sin ningún recurso con certificación vigente, la oferta se omite de `ofertas_validadas` (responde `200 OK` con lista vacía).
* **Tag Swagger:** `Ofertas`
* **Requiere Autenticación:** **Sí** (Bearer JWT).

#### Parámetros

| Parámetro | Ubicación | Tipo | Requerido | Valores Permitidos / Restricciones | Descripción |
|---|---|---|---|---|---|
| `id_emergencia` | Body (JSON) | `integer` | **Sí** | Entero mayor a 0 | ID de la emergencia municipal |
| `tipo_desastre` | Body (JSON) | `string` | **Sí** | `"geologico"`, `"meteorologico"`, `"hidrologico"`, `"biologico"`, `"incendio_forestal"` | Tipo de catástrofe a enfrentar |
| `gravedad` | Body (JSON) | `string` | **Sí** | `"bajo"`, `"medio"`, `"alto"`, `"critico"` | Nivel de severidad de la emergencia (masculino) |
| `ofertas` | Body (JSON) | `array` | **Sí** | Mínimo 1 elemento, sin `id_oferta` duplicados | Lista de ofertas a evaluar |
| ↳ `id_oferta` | Objeto | `integer` | **Sí** | Entero mayor a 0 | ID de la oferta |
| ↳ `id_ong` | Objeto | `integer` | **Sí** | Entero mayor a 0 | ID de la ONG que presenta la oferta |
| ↳ `es_conjunta` | Objeto | `boolean` | **Sí** | `true` o `false` | Indica si participan varias organizaciones |
| ↳ `recursos` | Objeto | `array` | **Sí** | Mínimo 1 elemento, sin `id_recurso` duplicados | Recursos ofrecidos |
| ↳↳ `id_recurso` | Objeto | `integer` | **Sí** | Entero mayor a 0 | Identificador del recurso |
| ↳↳ `cantidad_ofrecida` | Objeto | `integer` | **Sí** | Entero mayor a 0 | Cantidad ofrecida |

---

#### Caso 1: Validación Exitosa con Evaluación Cualitativa (HTTP 200 OK)
Evalúa una oferta de la ONG 3 para un desastre hidrológico grave. Como la ONG cuenta con habilitación principal en el Recurso 10 y secundaria en el 12, ambos son evaluados y categorizados según sus competencias.

* **Request body:**
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
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
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

---

#### Caso 2: Recurso no Certificado Omitido Silenciosamente (HTTP 200 OK)
La ONG 4 ofrece el Recurso 10 (cuya certificación para `hidrologico` está **vencida**). El sistema no rechaza con error 404, sino que omite el recurso no certificado. Como la oferta no contiene otros recursos válidos, la oferta se omite de la lista de validadas.

* **Request body:**
  ```json
  {
    "id_emergencia": 102,
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
  }
  ```
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "id_emergencia": 102,
    "estado_general": "validado",
    "ofertas_validadas": []
  }
  ```

---

#### Caso 3: Omisión Parcial de Recursos sin Certificación (HTTP 200 OK)
La ONG 3 ofrece el Recurso 10 (certificado) y el Recurso 20 (generador eléctrico existente en catálogo pero sin certificación). El Recurso 20 se descarta y el Recurso 10 se aprueba con `lote_principal`.

* **Request body:**
  ```json
  {
    "id_emergencia": 103,
    "tipo_desastre": "hidrologico",
    "gravedad": "alto",
    "ofertas": [
      {
        "id_oferta": 21,
        "es_conjunta": false,
        "id_ong": 3,
        "recursos": [
          { "id_recurso": 10, "cantidad_ofrecida": 20 },
          { "id_recurso": 20, "cantidad_ofrecida": 2 }
        ]
      }
    ]
  }
  ```
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:** En `recursos_evaluados` únicamente aparece el recurso 10.

---

#### Caso 4: ONG Inexistente o Inhabilitada (HTTP 404 Not Found)
Si se envía una oferta de una organización inhabilitada (como la ONG 5) o inexistente en el catálogo nacional (ejemplo ONG 999).

* **Request body:**
  ```json
  {
    "id_emergencia": 104,
    "tipo_desastre": "hidrologico",
    "gravedad": "alto",
    "ofertas": [
      {
        "id_oferta": 22,
        "es_conjunta": false,
        "id_ong": 5,
        "recursos": [
          { "id_recurso": 10, "cantidad_ofrecida": 5 }
        ]
      }
    ]
  }
  ```
* **Código HTTP esperado:** `404 Not Found`
* **Respuesta esperada:**
  ```json
  {
    "detail": "La ONG 5 no está habilitada."
  }
  ```

---

#### Caso 5: Error de Validación de Esquema Enum (HTTP 422 Unprocessable Entity)
Si se envía un valor que no pertenece a los enums permitidos (ejemplo `gravedad: "alta"` en femenino o `tipo_desastre: "inundacion"` en lugar de `"hidrologico"`).

* **Request body:**
  ```json
  {
    "id_emergencia": 105,
    "tipo_desastre": "inundacion",
    "gravedad": "alta",
    "ofertas": [
      {
        "id_oferta": 23,
        "es_conjunta": false,
        "id_ong": 3,
        "recursos": [
          { "id_recurso": 10, "cantidad_ofrecida": 5 }
        ]
      }
    ]
  }
  ```
* **Código HTTP esperado:** `422 Unprocessable Entity`
* **Respuesta esperada:** Detalle de validación indicando los valores permitidos para el enum.

---

## 7. Adjudicación y Bloqueo Concurrente de Recursos (Ofertas)

### `POST /api/v1/ofertas/adjudicar`

Bloquea y reserva transaccionalmente el stock en PostgreSQL (`with_for_update`) para garantizar que múltiples pedidos concurrentes no produzcan stock negativo. Es **idempotente**: enviar repetidamente la misma adjudicación para la misma emergencia no descuenta doble stock.

* **Tag Swagger:** `Ofertas`
* **Requiere Autenticación:** **Sí** (Bearer JWT).

#### Parámetros

| Parámetro | Ubicación | Tipo | Requerido | Restricciones | Descripción |
|---|---|---|---|---|---|
| `id_emergencia` | Body (JSON) | `integer` | **Sí** | Entero mayor a 0 | ID de la emergencia adjudicada |
| `ofertas_adjudicadas` | Body (JSON) | `array` | **Sí** | Mínimo 1 elemento, sin `id_oferta` duplicados | Lista de ofertas seleccionadas por el Municipio |
| ↳ `id_oferta` | Objeto | `integer` | **Sí** | Entero mayor a 0 | Identificador de la oferta |
| ↳ `id_ong` | Objeto | `integer` | **Sí** | Entero mayor a 0 | Identificador de la ONG adjudicada |
| ↳ `recursos` | Objeto | `array` | **Sí** | Mínimo 1 elemento, sin `id_recurso` duplicados | Recursos y cantidades a bloquear |
| ↳↳ `id_recurso` | Objeto | `integer` | **Sí** | Entero mayor a 0 | Identificador del recurso |
| ↳↳ `cantidad_adjudicada` | Objeto | `integer` | **Sí** | Entero mayor a 0 | Cantidad a bloquear |

---

#### Caso 1: Bloqueo Exitoso Total (HTTP 200 OK)
Se adjudican 50 unidades del Recurso 10 a la ONG 3 para la emergencia 501. El stock disponible de la ONG 3 baja de 80 a 30.

* **Request body:**
  ```json
  {
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
  }
  ```
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "id_emergencia": 501,
    "estado": "bloqueo_exitoso",
    "mensaje": "Los recursos han sido comprometidos transaccionalmente a nivel nacional.",
    "timestamp_bloqueo": "2026-10-23T10:00:00Z",
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

---

#### Caso 2: Prueba de Idempotencia (HTTP 200 OK sin Descuento Duplicado)
Volvé a ejecutar exactamente la misma petición del **Caso 1** en Swagger (mismo `id_emergencia: 501`, misma oferta y cantidad).

* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:** Responde con `bloqueo_exitoso`. Si luego consultás `GET /api/v1/recursos/disponibilidad?id_ong=3&recurso_id=10`, comprobarás que el stock disponible sigue en 30 (no bajó a -20).

---

#### Caso 3: Bloqueo Parcial con Detalle de Rechazadas (HTTP 200 OK)
Se envían dos ofertas en la misma solicitud: la Oferta 30 (pide 10 botes, habiendo 30 disponibles) y la Oferta 31 (pide 999 botes, superando el stock disponible). El endpoint adjudica la primera y rechaza la segunda sin cancelar toda la transacción.

* **Request body:**
  ```json
  {
    "id_emergencia": 502,
    "ofertas_adjudicadas": [
      {
        "id_oferta": 30,
        "id_ong": 3,
        "recursos": [
          { "id_recurso": 10, "cantidad_adjudicada": 10 }
        ]
      },
      {
        "id_oferta": 31,
        "id_ong": 3,
        "recursos": [
          { "id_recurso": 10, "cantidad_adjudicada": 999 }
        ]
      }
    ]
  }
  ```
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "id_emergencia": 502,
    "estado": "bloqueo_parcial",
    "mensaje": "Se adjudicaron parcialmente las ofertas con disponibilidad suficiente.",
    "timestamp_bloqueo": "2026-10-23T10:00:00Z",
    "ofertas_adjudicadas": [
      {
        "id_oferta": 30,
        "id_ong": 3,
        "estado": "adjudicada"
      }
    ],
    "ofertas_rechazadas": [
      {
        "id_oferta": 31,
        "id_ong": 3,
        "motivo": "No fue posible adjudicar todos los recursos de la oferta",
        "recursos_sin_stock": [
          {
            "id_recurso": 10,
            "cantidad_solicitada": 999,
            "cantidad_disponible": 20,
            "motivo": "stock_insuficiente"
          }
        ]
      }
    ]
  }
  ```

---

#### Caso 4: Bloqueo Fallido Total por Falta de Stock (HTTP 409 Conflict)
Se intenta adjudicar una oferta donde ningún recurso dispone de inventario suficiente (ejemplo: pedir 99,999 botes para la emergencia 503). La API ejecuta un rollback completo y devuelve 409 Conflict.

* **Request body:**
  ```json
  {
    "id_emergencia": 503,
    "ofertas_adjudicadas": [
      {
        "id_oferta": 40,
        "id_ong": 3,
        "recursos": [
          { "id_recurso": 10, "cantidad_adjudicada": 99999 }
        ]
      }
    ]
  }
  ```
* **Código HTTP esperado:** `409 Conflict`
* **Respuesta esperada:**
  ```json
  {
    "detail": {
      "id_emergencia": 503,
      "estado": "bloqueo_fallido",
      "mensaje": "Ninguna oferta pudo ser adjudicada por falta de stock o inconsistencias.",
      "ofertas_rechazadas": [
        {
          "id_oferta": 40,
          "id_ong": 3,
          "motivo": "No fue posible adjudicar todos los recursos de la oferta",
          "recursos_sin_stock": [
            {
              "id_recurso": 10,
              "cantidad_solicitada": 99999,
              "cantidad_disponible": 20,
              "motivo": "stock_insuficiente"
            }
          ]
        }
      ]
    }
  }
  ```

---

## 8. Cierre de Proyecto y Liberación de Recursos (Proyectos)

### `POST /api/v1/proyectos/liberar-recursos`

Restaura los recursos comprometidos durante la emergencia devolviéndolos al inventario disponible de la ONG. Marca los compromisos como `LIBERADO` de forma transaccional.

* **Tag Swagger:** `Proyectos`
* **Requiere Autenticación:** **Sí** (Bearer JWT).

#### Parámetros

| Parámetro | Ubicación | Tipo | Requerido | Restricciones | Descripción |
|---|---|---|---|---|---|
| `id_emergencia` | Body (JSON) | `integer` | **Sí** | Entero mayor a 0 | ID de la emergencia que finaliza tareas |
| `id_ong` | Body (JSON) | `integer` | **Sí** | Entero mayor a 0 | ID de la organización cuyos recursos se liberan |
| `motivo_cierre` | Body (JSON) | `string` | **Sí** | Entre 1 y 50 caracteres | Motivo administrativo del cierre (ej: `"finalizacion_tareas"`) |
| `recursos_a_liberar` | Body (JSON) | `array` | No | Lista opcional | Si se envía vacía o se omite, se liberan **todos** los recursos comprometidos para esa emergencia y ONG |

---

#### Caso 1: Liberación Exitosa de Recursos Comprometidos (HTTP 200 OK)
Libera los recursos bloqueados en el paso 7 para la emergencia 501 y la ONG 3.

* **Request body:**
  ```json
  {
    "id_emergencia": 501,
    "id_ong": 3,
    "motivo_cierre": "finalizacion_tareas",
    "recursos_a_liberar": [
      {
        "id_recurso": 10,
        "cantidad_liberada": 50
      }
    ]
  }
  ```
* **Código HTTP esperado:** `200 OK`
* **Respuesta esperada:**
  ```json
  {
    "estado": "liberacion_exitosa",
    "id_ong": 3,
    "mensaje": "Recursos liberados. Disponibilidad global actualizada.",
    "total_recursos_liberados": 50
  }
  ```
* **Criterio de validación:** Si se consulta nuevamente `GET /api/v1/recursos/disponibilidad?id_ong=3&recurso_id=10`, el stock disponible se habrá incrementado en 50 unidades.

---

#### Caso 2: Liberación sin Compromisos Activos (HTTP 404 Not Found)
Si se intenta liberar una emergencia que no tiene recursos comprometidos, o si se vuelve a enviar la solicitud del Caso 1 cuando los recursos ya fueron restituidos.

* **Request body:**
  ```json
  {
    "id_emergencia": 999999,
    "id_ong": 3,
    "motivo_cierre": "finalizacion_tareas",
    "recursos_a_liberar": []
  }
  ```
* **Código HTTP esperado:** `404 Not Found`
* **Respuesta esperada:**
  ```json
  {
    "detail": "No se encontraron recursos comprometidos activos para la emergencia 999999 y ONG 3."
  }
  ```

---

## 9. Matriz Resumen de Códigos HTTP del Sistema

| Código HTTP | Significado | Escenarios en la API |
|---|---|---|
| **200 OK** | Petición exitosa | Consultas GET, `login`, `validar` (incluso si omite recursos no certificados), `liberar-recursos` y `adjudicar` (`bloqueo_exitoso` o `bloqueo_parcial`). |
| **201 Created** | Creación exitosa | `POST /api/v1/ongs` al registrar una nueva organización. |
| **401 Unauthorized** | Autenticación requerida | Token Bearer JWT ausente, expirado o credenciales erróneas en login. |
| **404 Not Found** | Recurso o referencia no encontrada | ONG inexistente o inhabilitada en validación; o liberación de una emergencia sin compromisos activos. |
| **409 Conflict** | Conflicto de estado de datos | ID duplicado en `POST /api/v1/ongs`; o falta total de stock en todas las ofertas de `POST /api/v1/ofertas/adjudicar`. |
| **422 Unprocessable** | Inconsistencia de contrato | Errores en tipos de datos, enteros negativos o cadenas fuera de los enums permitidos (`gravedad`, `tipo_desastre`). |
| **503 Unavailable** | Base de datos no accesible | Fallo de conexión con el motor PostgreSQL. |
