# DSSD Servicio Externo API

Base modular para una API con FastAPI y Python, preparada para ejecutarse en Docker.

## Requisitos

- Docker Engine
- Docker Compose (plugin `docker compose`)

No es necesario instalar Python ni dependencias en el entorno local: se instalan y ejecutan dentro del contenedor.

## Configurar PostgreSQL en Render

`.env.example` es solo una plantilla y no contiene credenciales reales. Creá tu archivo `.env` a partir de ella:

```powershell
Copy-Item .env.example .env
```

Editá `.env` y reemplazá el marcador de `DATABASE_URL` por la URL de conexión de PostgreSQL provista por Render. No compartas ni subas `.env` a Git. La URL externa suele usarse desde la computadora local; la URL interna suele usarse desde un servicio alojado en la misma red privada de Render. Confirmá en la configuración actual de Render cuál corresponde a tu servicio.

## Construir e iniciar

Desde la raíz del proyecto:

```sh
docker compose up --build
```

Compose publica el puerto `8000` y monta el código del proyecto dentro del contenedor. Uvicorn usa `--reload`, por lo que los cambios en el código se reflejan automáticamente durante el desarrollo, sin reconstruir la imagen. Para iniciar en segundo plano:

```sh
docker compose up --build -d
```

## Probar la API

- Estado: <http://localhost:8000/health> — devuelve `{"status":"ok"}`.
- Conexión a PostgreSQL: <http://localhost:8000/health/db> — ejecuta `SELECT 1`; devuelve `{"status":"ok"}` si la conexión está disponible y HTTP 503 si falta la configuración o no se puede conectar.
- Documentación interactiva: <http://localhost:8000/docs>.

La configuración de la base de datos se carga desde `.env` mediante Docker Compose. La URL no se incluye en la imagen ni en las respuestas de la API.

## Detener

```sh
docker compose down
```

## Estructura

- `app/main.py`: creación de la aplicación FastAPI y registro de rutas.
- `app/api/routes/`: endpoints de la API.
- `app/core/`: configuración general.
- `app/db/`: engine y sesiones de SQLAlchemy.
- `app/models/`: futuros modelos de datos.
- `app/schemas/`: esquemas de validación.
- `app/services/`: futura lógica de negocio.
