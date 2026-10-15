# DSSD Servicio Externo API

Base modular para una API con FastAPI y Python, preparada para ejecutarse en Docker.

## Requisitos

- Docker Engine
- Docker Compose (plugin `docker compose`)

No es necesario instalar Python ni dependencias en el entorno local: se instalan y ejecutan dentro del contenedor.

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
- Documentación interactiva: <http://localhost:8000/docs>.

## Detener

```sh
docker compose down
```

## Estructura

- `app/main.py`: creación de la aplicación FastAPI y registro de rutas.
- `app/api/routes/`: endpoints de la API.
- `app/core/`: configuración general.
- `app/db/`: futura conexión a la base de datos.
- `app/models/`: futuros modelos de datos.
- `app/schemas/`: esquemas de validación.
- `app/services/`: futura lógica de negocio.
