# DSSD Servicio Externo API

Base modular para una API con FastAPI y Python, preparada para ejecutarse en Docker.

## Requisitos

- Docker Engine
- Docker Compose (plugin `docker compose`)

No es necesario instalar Python ni dependencias en el entorno local: se instalan y ejecutan dentro del contenedor.

## Configurar PostgreSQL y JWT

`.env.example` es solo una plantilla y no contiene credenciales reales. Si todavía no tenés un `.env`, crealo desde la plantilla:

```powershell
Copy-Item .env.example .env
```

Si ya existe un `.env`, editá ese archivo sin sobrescribirlo. Reemplazá `DATABASE_URL` con la URL de PostgreSQL provista por Render. La URL externa suele utilizarse desde la computadora local; la interna, desde un servicio en la misma red privada de Render. Confirmá cuál corresponde a tu configuración en Render.

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

## Migraciones y usuario inicial

Aplicá la migración de la tabla `users` después de configurar `.env`:

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

El comando solicita email y contraseña dos veces, no imprime la contraseña, exige al menos 12 caracteres y almacena únicamente su hash Argon2. Ejecutalo después de aplicar las migraciones.

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
- `app/services/`: futura lógica de negocio.
