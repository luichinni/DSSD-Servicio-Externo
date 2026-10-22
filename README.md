# DSSD Servicio Externo API

API para consultar ONGs habilitadas y disponibilidad de recursos, y validar las competencias de las ONGs para los recursos ofrecidos ante una emergencia. Está desarrollada con FastAPI y PostgreSQL y se ejecuta con Docker.

Recibe solicitudes JSON desde Bonita y devuelve la clasificación de los aportes según las certificaciones registradas. La aplicación local y este servicio utilizan bases de datos separadas.

## Requisitos

- Docker Engine
- Docker Compose (plugin `docker compose`)

No es necesario instalar Python ni dependencias en el entorno local: se instalan y ejecutan dentro del contenedor.

## Configurar PostgreSQL y JWT

`.env.example` es solo una plantilla y no contiene credenciales reales. Si todavía no tenés un `.env`, crealo desde la plantilla:

```powershell
Copy-Item .env.example .env
```

Si ya existe un `.env`, editá ese archivo sin sobrescribirlo. Para usar PostgreSQL local con Docker Compose, conservá los valores de conexión de la plantilla, que coinciden con el servicio `db` de `compose.yaml`. Las credenciales incluidas son solo para desarrollo local.

Si usás una base alojada en Render, reemplazá `DATABASE_URL` con su URL de conexión. La URL externa se utiliza fuera de su red privada; la interna, desde un servicio en esa misma red. Las migraciones y los comandos de carga actuarán sobre la base indicada por `DATABASE_URL`.

Generá un secreto JWT aleatorio de al menos 32 bytes sin instalar Python localmente:

```sh
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copiá el resultado a `JWT_SECRET_KEY` en `.env`. Conservá `JWT_ALGORITHM=HS256` y ajustá `ACCESS_TOKEN_EXPIRE_MINUTES` si corresponde. No publiques ni compartas `.env`; está excluido de Git y de la imagen Docker.

## Construir e iniciar

Desde la raíz del proyecto:

```sh
docker compose up --build
```

Compose publica el puerto `8000` y monta el código del proyecto dentro del contenedor. Uvicorn usa `--reload`, por lo que los cambios en el código se reflejan automáticamente durante el desarrollo, sin reconstruir la imagen. Para iniciar en segundo plano:

```sh
docker compose up --build -d
```

PostgreSQL se publica en `localhost:5433` para permitir que conviva con otra base en el puerto `5432`. La API se conecta por la red interna de Docker a `db:5432`; conservá `POSTGRES_HOST=db` y `POSTGRES_PORT=5432` en `.env` para usar esta base local.

## Migraciones y usuario inicial

Aplicá las migraciones de usuarios, certificaciones y catálogos nacionales después de configurar `.env`:

```sh
docker compose exec api alembic upgrade head
```

Para generar migraciones futuras luego de modificar modelos:

```sh
docker compose exec api alembic revision --autogenerate -m "descripcion_del_cambio"
docker compose exec api alembic upgrade head
```

No se crean tablas ni usuarios durante el arranque de la API. Para crear el primer usuario explícitamente, ejecutá el comando interactivo dentro del contenedor:

```sh
docker compose exec api python -m app.cli.create_user
```

El comando solicita un email y una contraseña elegidos por vos, y pide confirmar la contraseña. No imprime la contraseña, exige al menos 12 caracteres y almacena únicamente su hash Argon2. Ejecutalo después de aplicar las migraciones.

## Probar la API

- Estado: <http://localhost:8000/health> — devuelve `{"status":"ok"}`.
- Conexión a PostgreSQL: <http://localhost:8000/health/db> — ejecuta `SELECT 1`; devuelve `{"status":"ok"}` si la conexión está disponible y HTTP 503 si falta la configuración o no se puede conectar.
- Documentación interactiva: <http://localhost:8000/docs>.

En Swagger, abrí `POST /auth/login`, seleccioná **Try it out**, ingresá el email y la contraseña del usuario creado, y ejecutá la solicitud. La respuesta incluye `access_token`. Luego elegí **Authorize**, pegá el token y confirmá; Swagger lo enviará como `Authorization: Bearer <access_token>` al ejecutar `GET /auth/me`. La respuesta de `/auth/me` contiene solo el identificador y el email.

Para ejecutar las pruebas automatizadas dentro de Docker:

```sh
docker compose run --build --rm api python -m pytest -q
```

La configuración de PostgreSQL se carga desde `.env` mediante Docker Compose. Ni la URL ni la clave JWT se incluyen en la imagen o en las respuestas de la API.

## Endpoints Transaccionales (Dev 5: Core - Transaccional)

### 1. Adjudicación y Bloqueo Concurrente
- **Endpoint:** `POST /api/v1/ofertas/adjudicar`
- **Headers:** `Authorization: Bearer <TOKEN>`
- **Payload:**
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
- **Respuesta (200 OK):**
```json
{
  "id_emergencia": 101,
  "estado": "bloqueo_exitoso",
  "mensaje": "Los recursos han sido comprometidos transaccionalmente a nivel nacional.",
  "timestamp_bloqueo": "2026-10-17T15:30:00Z",
  "ofertas_adjudicadas": [{"id_oferta": 15, "id_ong": 3, "estado": "adjudicada"}],
  "ofertas_rechazadas": []
}
```
Si ninguna oferta cuenta con stock disponible suficiente, devuelve **HTTP 409 Conflict**.

### 2. Liberación de Recursos y Cierre
- **Endpoint:** `POST /api/v1/proyectos/liberar-recursos`
- **Headers:** `Authorization: Bearer <TOKEN>`
- **Payload:**
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
- **Respuesta (200 OK):**
```json
{
  "estado": "liberacion_exitosa",
  "id_ong": 3,
  "mensaje": "Recursos liberados. Disponibilidad global actualizada.",
  "total_recursos_liberados": 50
}
```

## Detener

```sh
docker compose down
```


## Estructura

- `app/main.py`: creación de la aplicación FastAPI y registro de rutas.
- `app/api/routes/`: endpoints de la API.
- `app/core/`: configuración general.
- `app/db/`: engine y sesiones de SQLAlchemy.
- `app/models/`: modelos SQLAlchemy.
- `app/schemas/`: esquemas Pydantic.
- `alembic/`: configuración y migraciones de base de datos.
- `app/services/`: lógica de catálogos y validación por competencias.

## Validación por competencias

`POST /api/v1/ofertas/validar` recibe la emergencia, las ofertas y los recursos de cada ONG. Comprueba que las ONGs estén habilitadas y que los recursos existan. Los recursos sin certificaciones vigentes aplicables al tipo de desastre se omiten; los recursos restantes se clasifican como `lote_principal` o `apoyo_secundario`. Si una oferta queda sin recursos certificados, no se incluye en `ofertas_validadas`. Requiere JWT y no reserva recursos. El contrato de solicitud y respuesta está disponible en Swagger.

Si una ONG no existe o está inhabilitada, o un recurso no existe en el catálogo, devuelve HTTP 404. Los datos de entrada inválidos devuelven 422 y los errores de acceso a la base, 503.

Para cargar certificaciones ficticias en una base de desarrollo, después de aplicar las migraciones:

```sh
docker compose exec api python -m app.cli.seed_certificaciones_demo
```

La carga crea ONGs ficticias 3 y 4, recursos 10 y 12, inventario y certificaciones para `hidrologico`. Conserva los registros reales existentes y su habilitación/stock; únicamente completa los registros pendientes de esos IDs creados por la migración a partir de certificados antiguos. Si habías cargado ejemplos con `inundacion`, los certificados anteriores se conservan. Usar solo en desarrollo.

Para probar la validación desde Swagger, autorizá con el JWT y enviá el contenido de [examples/validacion.json](examples/validacion.json). Con los datos demo, la ONG 3 devuelve el recurso 10 como principal y el recurso 12 como apoyo.

Los endpoints de adjudicación y liberación están implementados (transaccionales, con bloqueo de filas de `inventario`). La integración del flujo completo con Bonita aún requiere una prueba desde su conector real.

## Catálogos nacionales

Todos estos endpoints requieren JWT:

- `POST /api/v1/ongs`: alta con `id_ong` de la app local, `nombre` y `descripcion` opcional. Un ID repetido devuelve 409 sin sobrescribir datos.
- `GET /api/v1/ongs/habilitadas`: devuelve el total, las ONGs habilitadas y sus certificaciones vigentes.
- `GET /api/v1/recursos/disponibilidad`: disponibilidad por ONG y recurso; admite `?recurso_id=10&id_ong=3`. Cantidad comprometida = total menos disponible.

Se usan IDs enteros de la app local en ONGs y recursos, proporcionados explícitamente: no se asignan IDs independientes. Las bases siguen separadas y sus catálogos deben cargarse con las mismas entidades e IDs; no hay sincronización automática.

La migración `20261020_0003` crea catálogos/inventario y claves foráneas de certificaciones. Si había certificados antiguos sin catálogo, conserva esos datos y crea referencias pendientes; las ONGs quedan deshabilitadas hasta completar/verificar su información.
