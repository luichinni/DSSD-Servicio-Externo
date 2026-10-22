import logging

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.routes import auth_router, health_router, ofertas_router, ongs_router
from app.api.routes.catalogo import router as catalogo_router
from app.api.routes.proyectos import router as proyectos_router
from app.core.config import DatabaseConfigurationError, JWTConfigurationError
from app.core.openapi import (
    API_DESCRIPTION,
    API_SUMMARY,
    API_TITLE,
    API_VERSION,
    TAGS_METADATA,
)

app = FastAPI(
    title=API_TITLE,
    summary=API_SUMMARY,
    description=API_DESCRIPTION,
    version=API_VERSION,
    openapi_tags=TAGS_METADATA,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(catalogo_router, prefix="/api/v1")
app.include_router(ongs_router, prefix="/api/v1")
app.include_router(ofertas_router, prefix="/api/v1")
app.include_router(proyectos_router, prefix="/api/v1")


def custom_openapi() -> dict:
    if app.openapi_schema is not None:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    security_schemes = schema.get("components", {}).get("securitySchemes", {})
    for name, scheme in security_schemes.items():
        if scheme.get("type") == "oauth2":
            security_schemes[name] = {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.exception_handler(DatabaseConfigurationError)
async def database_configuration_error_handler(
    request: Request,
    exc: DatabaseConfigurationError,
) -> JSONResponse:
    logging.getLogger(__name__).error("%s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable"},
    )


@app.exception_handler(JWTConfigurationError)
async def jwt_configuration_error_handler(
    request: Request,
    exc: JWTConfigurationError,
) -> JSONResponse:
    logging.getLogger(__name__).error("%s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Authentication is not configured"},
    )
