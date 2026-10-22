# Guía de Integración Técnica: Flask -> Bonita BPM -> API Externa (RescueSync)

Esta guía detalla la arquitectura de integración y los pasos de configuración para conectar **`DSSD-Flask-App` (Cliente)** con **Bonita Open Solution (Orquestador BPM)** y la **API del Sistema Nacional `DSSD-Servicio-Externo` (Servicio Backend)** desplegada en `[API_BASE_URL]`.

---

## 1. Arquitectura General y Flujo de Comunicación

```
+-------------------+                   +-------------------+                   +------------------------+
|  DSSD-Flask-App   |  REST (Contratos) |    Bonita BPM     | REST (Conectores) |  DSSD-Servicio-Externo |
|     (Cliente)     | ----------------> |  (Orquestación)   | ----------------> |   ([API_BASE_URL])     |
|                   | <---------------- |                   | <---------------- |                        |
+-------------------+  Polling/Contexto +-------------------+  JSON Responses   +------------------------+
```

### Momentos Clave del Ciclo de Vida:
1. **Autenticación en la API Externa:** Bonita obtiene un JWT Bearer llamando a `POST [API_BASE_URL]/api/v1/auth/login`.
2. **Momento 1 - Validación por Competencias:** Tras recibirse las ofertas de las ONGs en una convocatoria, Bonita invoca `POST [API_BASE_URL]/api/v1/ofertas/validar` para obtener perfiles y clasificación de roles (`lote_principal` o `apoyo_secundario`).
3. **Momento 2 - Adjudicación y Bloqueo:** El Municipio selecciona las ofertas ganadoras y Bonita invoca `POST [API_BASE_URL]/api/v1/ofertas/adjudicar` para reservar transaccionalmente el stock en PostgreSQL (`with_for_update`).
4. **Momento 3 - Cierre y Liberación:** Al finalizar las tareas operativas de las ONGs, Bonita invoca `POST [API_BASE_URL]/api/v1/proyectos/liberar-recursos` para restituir el stock al inventario nacional.

---

## 2. Bloque 1: Comunicación Flask -> Bonita

### Comparativa: JSON Nativo (Contratos) vs. Strings Serializados

| Característica | Enfoque A: JSON Nativo (Contratos COMPLEX) - **RECOMENDADO** | Enfoque B: Strings Serializados (Pasamanos Clásico) |
| :--- | :--- | :--- |
| **Definición en Bonita** | Inputs de Contrato de tipo `COMPLEX` y `LIST OF COMPLEX`. | Variable de proceso tipo `java.lang.String` o input `TEXT`. |
| **Envío desde Flask** | Envío de diccionarios Python estándar: `datos = {"id_emergencia": 101, ...}`. | Doble serialización: `{"payload_json": json.dumps(datos)}`. |
| **Validación de Tipos** | Bonita valida estructura, requeridos y tipos numéricos antes de instanciar. | No hay validación en Bonita; cualquier string malformado pasa. |
| **Manipulación en Groovy**| Acceso directo a mapas y listas: `mapa.ofertas[0].recursos`. | Requiere `new JsonSlurper().parseText(...)` en cada paso. |

### Implementación en Python (`DSSD-Flask-App`)

Aprovechando el cliente existente `_ClienteBonita` en `src/core/services/bonita.py`:

```python
# src/core/services/bonita_integracion.py
import json
from src.core.services.bonita import _ClienteBonita, _id

# -------------------------------------------------------------------------
# ENFOQUE A (RECOMENDADO): JSON Nativo contra Process/Task Contracts
# -------------------------------------------------------------------------
def enviar_ofertas_a_validar_nativo(case_id: int, task_name: str, payload_validacion: dict):
    """
    payload_validacion es un dict Python limpio con:
    id_emergencia, tipo_desastre, gravedad, ofertas.
    """
    cliente = _ClienteBonita()
    # Se completa la tarea humana enviando el diccionario directo al contrato de la tarea
    cliente.completar(case_id, task_name, {
        "solicitud_validacion_input": payload_validacion
    })

def adjudicar_ofertas_nativo(case_id: int, task_name: str, payload_adjudicacion: dict):
    """
    payload_adjudicacion es un dict Python limpio con:
    id_emergencia, ofertas_adjudicadas.
    """
    cliente = _ClienteBonita()
    cliente.completar(case_id, task_name, {
        "solicitud_adjudicacion_input": payload_adjudicacion
    })

def liberar_recursos_nativo(case_id: int, task_name: str, payload_liberacion: dict):
    cliente = _ClienteBonita()
    cliente.completar(case_id, task_name, {
        "solicitud_liberacion_input": payload_liberacion
    })

# -------------------------------------------------------------------------
# ENFOQUE B (CONTINGENCIA): String Serializado
# -------------------------------------------------------------------------
def enviar_payload_como_string(case_id: int, task_name: str, payload_dict: dict):
    cliente = _ClienteBonita()
    payload_str = json.dumps(payload_dict)
    cliente.completar(case_id, task_name, {
        "payload_json_str_input": payload_str
    })
```

---

## 3. Bloque 2: Configuración en Bonita BPM

### 3.1. Variables de Proceso a Declarar

En Bonita Studio, sobre el pool principal del proceso:
1. `token_api_externa` (Tipo: `java.lang.String`): Almacena el JWT Bearer para las llamadas subsiguientes.
2. `resultado_validacion` (Tipo: `java.util.Map` o `java.lang.String`): Respuesta de `/ofertas/validar`.
3. `resultado_adjudicacion` (Tipo: `java.util.Map` o `java.lang.String`): Respuesta de `/ofertas/adjudicar`.
4. `codigo_http_adjudicacion` (Tipo: `java.lang.Integer`): Código de respuesta (200 o 409).
5. `resultado_liberacion` (Tipo: `java.util.Map` o `java.lang.String`): Respuesta de `/proyectos/liberar-recursos`.

---

### 3.2. Conector REST: Autenticación (`POST /api/v1/auth/login`)

Configurar en una tarea de servicio al inicio del flujo (o antes de llamar a la API externa):
* **URL:** `"[API_BASE_URL]/api/v1/auth/login"`
* **HTTP Method:** `POST`
* **Headers:**
  * `Content-Type`: `application/json`
  * `Accept`: `application/json`
* **Body (Script Groovy):**
  ```groovy
  import groovy.json.JsonBuilder
  
  def credenciales = [
      email: "operador@emergencias.gob.ar",
      password: "password_segura_123" // Credencial configurada en el despliegue
  ]
  return new JsonBuilder(credenciales).toString()
  ```
* **Salida del Conector (Outputs):**
  * Variable de destino: `token_api_externa`
  * Expresión Groovy de salida:
    ```groovy
    // Si se usa bodyAsObject nativo del conector REST de Bonita:
    if (bodyAsObject != null && bodyAsObject.access_token != null) {
        return bodyAsObject.access_token
    }
    // Fallback parseando bodyAsString:
    def json = new groovy.json.JsonSlurper().parseText(bodyAsString)
    return json.access_token
    ```

---

### 3.3. Conector REST: Validación por Competencias (`POST /api/v1/ofertas/validar`)

* **URL:** `"[API_BASE_URL]/api/v1/ofertas/validar"`
* **HTTP Method:** `POST`
* **Headers:**
  * `Content-Type`: `application/json`
  * `Accept`: `application/json`
  * `Authorization`: `"Bearer " + token_api_externa`
* **Body (Script Groovy con datos de Contrato COMPLEX):**
  ```groovy
  import groovy.json.JsonBuilder

  // solicitud_validacion_input proviene del contrato completado por Flask
  def payload = [
      id_emergencia: solicitud_validacion_input.id_emergencia,
      tipo_desastre: solicitud_validacion_input.tipo_desastre.toLowerCase(), // ej: 'hidrologico'
      gravedad: solicitud_validacion_input.gravedad.toLowerCase(),           // ej: 'alto'
      ofertas: solicitud_validacion_input.ofertas.collect { o ->
          [
              id_oferta: o.id_oferta,
              es_conjunta: o.es_conjunta,
              id_ong: o.id_ong,
              recursos: o.recursos.collect { r ->
                  [
                      id_recurso: r.id_recurso,
                      cantidad_ofrecida: r.cantidad_ofrecida
                  ]
              }
          ]
      }
  ]
  return new JsonBuilder(payload).toString()
  ```
* **Salida del Conector (Outputs):**
  * Variable de destino: `resultado_validacion`
  * Expresión Groovy:
    ```groovy
    if (status == 200) {
        return (bodyAsObject != null) ? bodyAsObject : new groovy.json.JsonSlurper().parseText(bodyAsString)
    } else {
        throw new org.bonitasoft.engine.connector.ConnectorException("Error HTTP " + status + " en validación: " + bodyAsString)
    }
    ```

---

### 3.4. Conector REST: Adjudicación y Bloqueo (`POST /api/v1/ofertas/adjudicar`)

* **URL:** `"[API_BASE_URL]/api/v1/ofertas/adjudicar"`
* **HTTP Method:** `POST`
* **Headers:**
  * `Content-Type`: `application/json`
  * `Accept`: `application/json`
  * `Authorization`: `"Bearer " + token_api_externa`
* **Body (Script Groovy):**
  ```groovy
  import groovy.json.JsonBuilder

  def payload = [
      id_emergencia: solicitud_adjudicacion_input.id_emergencia,
      ofertas_adjudicadas: solicitud_adjudicacion_input.ofertas_adjudicadas.collect { o ->
          [
              id_oferta: o.id_oferta,
              id_ong: o.id_ong,
              recursos: o.recursos.collect { r ->
                  [
                      id_recurso: r.id_recurso,
                      cantidad_adjudicada: r.cantidad_adjudicada
                  ]
              }
          ]
      }
  ]
  return new JsonBuilder(payload).toString()
  ```
* **Captura de Respuestas y Control de Concurrencia (Outputs):**
  * `codigo_http_adjudicacion` = `status`
  * `resultado_adjudicacion` = `(bodyAsObject != null) ? bodyAsObject : new groovy.json.JsonSlurper().parseText(bodyAsString)`
* **Compuerta Exclusiva (XOR) posterior en Bonita:**
  * Transición **"Adjudicación Exitosa"**: Condición `codigo_http_adjudicacion == 200`
  * Transición **"Conflicto de Stock (409)"**: Condición `codigo_http_adjudicacion == 409` (Bifurca hacia tarea humana de revisión o notificación de rechazo).

---

### 3.5. Conector REST: Cierre y Liberación (`POST /api/v1/proyectos/liberar-recursos`)

* **URL:** `"[API_BASE_URL]/api/v1/proyectos/liberar-recursos"`
* **HTTP Method:** `POST`
* **Headers:**
  * `Content-Type`: `application/json`
  * `Accept`: `application/json`
  * `Authorization`: `"Bearer " + token_api_externa`
* **Body (Script Groovy):**
  ```groovy
  import groovy.json.JsonBuilder

  def payload = [
      id_emergencia: solicitud_liberacion_input.id_emergencia,
      id_ong: solicitud_liberacion_input.id_ong,
      motivo_cierre: "finalizacion_tareas",
      recursos_a_liberar: [] // Opcional: la API externa restituye todos los recursos comprometidos
  ]
  return new JsonBuilder(payload).toString()
  ```
* **Salida del Conector (Outputs):**
  * `resultado_liberacion` = `(bodyAsObject != null) ? bodyAsObject : new groovy.json.JsonSlurper().parseText(bodyAsString)`

---

## 4. Bloque 3: Bonita -> Flask (Consulta del Estado Procesado)

Una vez que Bonita procesa los conectores y avanza el flujo, Flask puede consultar los resultados mediante la API REST de Bonita:

### 4.1. Consulta vía Variables de Caso (`caseVariable`)
Flask puede consultar el resultado guardado en el caso mediante un `GET`:
```python
def obtener_resultado_adjudicacion(case_id: int) -> dict:
    cliente = _ClienteBonita()
    # Consulta la variable de proceso actualizada por el conector REST
    respuesta = cliente.pedir(
        f"/API/bpm/caseVariable/{case_id}/resultado_adjudicacion",
        method="GET",
        etapa="obtener resultado de adjudicación"
    )
    if not respuesta or "value" not in respuesta:
        return {}
    valor = respuesta["value"]
    # Si se guardó como string, se des-serializa; si fue objeto, ya viene parseado
    return json.loads(valor) if isinstance(valor, str) else valor
```

### 4.2. Consulta vía Contexto de Tarea Humana
Si el proceso se detiene en una tarea humana para el municipio (ej. *"Revisar Adjudicación"* o *"Verificar Conflicto 409"*):
```python
def obtener_contexto_tarea(task_id: int) -> dict:
    cliente = _ClienteBonita()
    # Devuelve los datos de contexto expuestos para esa tarea específica
    return cliente.pedir(f"/API/bpm/userTask/{task_id}/context", method="GET", etapa="leer contexto")
```

---

## 5. Resumen de Reglas de Formato para Bonita

1. **Valores Enum Estrictos:**
   * `tipo_desastre`: `"hidrologico"`, `"geologico"`, `"meteorologico"`, `"biologico"`, `"incendio_forestal"`.
   * `gravedad`: `"bajo"`, `"medio"`, `"alto"`, `"critico"`.
2. **IDs Numéricos:** `id_emergencia`, `id_ong`, `id_oferta`, `id_recurso` deben ser enteros positivos estrictos.
3. **Manejo de Errores HTTP en Conectores Bonita:**
   * **404:** Certificación vencida o no encontrada.
   * **409:** Stock insuficiente (`bloqueo_fallido`). Debe capturarse la variable de status para evitar que el conector falle como excepción no controlada.
   * **422:** Error de payload (revisar nombres de campos y enums).
